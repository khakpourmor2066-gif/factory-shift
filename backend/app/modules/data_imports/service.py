import json
import re
from datetime import UTC, date, datetime, time

from sqlalchemy.orm import Session

from app.modules.access_requests.service import normalize_mobile
from app.modules.change_management.model import AuditLog
from app.modules.data_imports.model import ImportError, ImportJob
from app.modules.data_imports.parser import parse_tabular_file
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.shifts.model import Schedule
from app.modules.users.model import User


EMPLOYEE_REQUIRED_COLUMNS = {
    "employee_code",
    "first_name",
    "last_name",
    "mobile",
    "department",
    "role",
}
SHIFT_REQUIRED_COLUMNS = {
    "employee_code",
    "shift_date",
    "shift_name",
    "shift_code",
    "start_time",
    "end_time",
}
ALLOWED_ROLES = {"EMPLOYEE", "SUPERVISOR", "HR", "ADMIN"}
PERSONNEL_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$")
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def create_import_preview(
    db: Session,
    import_type: str,
    filename: str,
    content: bytes,
    created_by: int,
) -> ImportJob:
    rows = parse_tabular_file(filename, content)
    normalized_type = import_type.upper()
    if normalized_type == "EMPLOYEE":
        valid_rows, errors = _validate_employee_rows(db, rows)
    elif normalized_type == "SHIFT":
        valid_rows, errors = _validate_shift_rows(db, rows)
    else:
        raise ValueError("نوع import پشتیبانی نمی‌شود.")

    rejected_rows = len({error["row_number"] for error in errors if error["row_number"] >= 2})
    job = ImportJob(
        import_type=normalized_type,
        filename=filename,
        status="PENDING",
        created_by=created_by,
        total_rows=len(rows),
        valid_rows=len(valid_rows),
        rejected_rows=rejected_rows,
        payload_json=json.dumps(valid_rows, ensure_ascii=False),
    )
    db.add(job)
    db.flush()
    for error in errors:
        db.add(ImportError(job_id=job.id, **error))
    db.commit()
    db.refresh(job)
    _write_audit(db, created_by, "import_preview_created", job)
    return job


def confirm_import(db: Session, job_id: int) -> ImportJob:
    job = get_import_job(db, job_id)
    if job.status != "PENDING":
        raise ValueError("فقط import در انتظار بررسی قابل تأیید است.")
    rows = json.loads(job.payload_json)
    try:
        if job.import_type == "EMPLOYEE":
            snapshots = _capture_employee_snapshots(db, rows)
            imported_rows = _apply_employee_rows(db, rows)
        elif job.import_type == "SHIFT":
            snapshots = _capture_shift_snapshots(db, rows)
            imported_rows = _apply_shift_rows(db, rows)
        else:
            raise ValueError("نوع import پشتیبانی نمی‌شود.")
        job.snapshot_json = json.dumps(snapshots, ensure_ascii=False)
        job.imported_rows = imported_rows
        job.status = "PARTIAL" if job.rejected_rows else "COMPLETED"
        job.completed_at = datetime.now(UTC)
        _add_audit(db, job.created_by, "import_confirmed", job)
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        failed_job = get_import_job(db, job_id)
        failed_job.status = "FAILED"
        failed_job.completed_at = datetime.now(UTC)
        db.commit()
        raise


def reject_import(db: Session, job_id: int) -> ImportJob:
    job = get_import_job(db, job_id)
    if job.status != "PENDING":
        raise ValueError("فقط import در انتظار بررسی قابل رد است.")
    job.status = "REJECTED"
    job.completed_at = datetime.now(UTC)
    _add_audit(db, job.created_by, "import_rejected", job)
    db.commit()
    db.refresh(job)
    return job


def rollback_import(db: Session, job_id: int, actor_user_id: int) -> ImportJob:
    job = get_import_job(db, job_id)
    if job.status not in {"COMPLETED", "PARTIAL"}:
        raise ValueError("فقط import تکمیل‌شده یا نیمه‌کامل قابل بازگردانی است.")
    if not job.snapshot_json:
        raise ValueError("snapshot لازم برای بازگردانی وجود ندارد.")
    snapshots = json.loads(job.snapshot_json)
    try:
        if job.import_type == "EMPLOYEE":
            _restore_employee_snapshots(db, snapshots)
        elif job.import_type == "SHIFT":
            _restore_shift_snapshots(db, snapshots)
        else:
            raise ValueError("نوع import پشتیبانی نمی‌شود.")
        job.status = "ROLLED_BACK"
        job.completed_at = datetime.now(UTC)
        _add_audit(db, actor_user_id, "import_rolled_back", job)
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        raise


def get_import_job(db: Session, job_id: int) -> ImportJob:
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if job is None:
        raise ValueError("درخواست import پیدا نشد.")
    return job


def list_import_jobs(db: Session, limit: int = 100) -> list[ImportJob]:
    return db.query(ImportJob).order_by(ImportJob.id.desc()).limit(limit).all()


def list_import_errors(db: Session, job_id: int) -> list[ImportError]:
    get_import_job(db, job_id)
    return db.query(ImportError).filter(ImportError.job_id == job_id).order_by(ImportError.row_number).all()


def list_import_records(db: Session, job_id: int) -> list[dict]:
    job = get_import_job(db, job_id)
    return [
        {"row_number": index, "data": row}
        for index, row in enumerate(json.loads(job.payload_json), start=2)
    ]


def employee_template() -> str:
    return (
        "employee_code,first_name,last_name,mobile,department,role,supervisor_code\n"
        "SUP-NEW-001,سارا,محمدی,09129999991,عملیات,SUPERVISOR,\n"
        "EMP-NEW-001,علی,احمدی,09129999992,عملیات,EMPLOYEE,SUP-NEW-001\n"
    )


def shift_template() -> str:
    return (
        "employee_code,shift_date,shift_name,shift_code,start_time,end_time\n"
        "EMP-001,2026-07-30,روز,DAY,08:00,16:00\n"
    )


def _validate_employee_rows(db: Session, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    missing_columns = EMPLOYEE_REQUIRED_COLUMNS - _headers(rows)
    if missing_columns:
        return [], [_file_error(f"ستون‌های الزامی وجود ندارند: {', '.join(sorted(missing_columns))}")]

    valid_rows = []
    errors = []
    seen_codes = set()
    seen_mobiles = set()
    file_codes = {row.get("employee_code", "").upper() for row in rows}
    active_employees = db.query(Employee).filter(Employee.is_active.is_(True)).all()
    database_codes = {employee.personnel_code for employee in active_employees}
    mobile_owners = {employee.mobile: employee.personnel_code for employee in active_employees}
    for row_number, row in enumerate(rows, start=2):
        code = row["employee_code"].upper()
        mobile = normalize_mobile(row["mobile"])
        role = row["role"].upper()
        row_errors = []
        if not PERSONNEL_CODE_PATTERN.fullmatch(code):
            row_errors.append(("employee_code", "invalid_employee_code", "کد کارمندی معتبر نیست."))
        if not row["first_name"] or not row["last_name"]:
            row_errors.append(("name", "missing_name", "نام و نام خانوادگی الزامی است."))
        if len(mobile) != 11 or not mobile.startswith("09") or not mobile.isdigit():
            row_errors.append(("mobile", "invalid_mobile", "شماره تلفن همراه معتبر نیست."))
        if not row["department"]:
            row_errors.append(("department", "missing_department", "واحد سازمانی الزامی است."))
        if role not in ALLOWED_ROLES:
            row_errors.append(("role", "invalid_role", "نقش کاربر معتبر نیست."))
        if code in seen_codes:
            row_errors.append(("employee_code", "duplicate_in_file", "کد کارمندی در فایل تکراری است."))
        if mobile in seen_mobiles:
            row_errors.append(("mobile", "duplicate_in_file", "شماره همراه در فایل تکراری است."))
        mobile_owner = mobile_owners.get(mobile)
        if mobile_owner is not None and mobile_owner != code:
            row_errors.append(("mobile", "mobile_conflict", "شماره همراه متعلق به کارمند دیگری است."))
        supervisor_code = row.get("supervisor_code", "").upper()
        if supervisor_code and supervisor_code not in file_codes | database_codes:
            row_errors.append(
                ("supervisor_code", "supervisor_not_found", "کد کارمندی سرپرست پیدا نشد.")
            )
        if row_errors:
            errors.extend(_row_errors(row_number, row, row_errors))
            continue
        seen_codes.add(code)
        seen_mobiles.add(mobile)
        valid_rows.append(
            {
                **row,
                "employee_code": code,
                "mobile": mobile,
                "role": role,
                "supervisor_code": supervisor_code,
            }
        )
    return valid_rows, errors


def _validate_shift_rows(db: Session, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    missing_columns = SHIFT_REQUIRED_COLUMNS - _headers(rows)
    if missing_columns:
        return [], [_file_error(f"ستون‌های الزامی وجود ندارند: {', '.join(sorted(missing_columns))}")]

    valid_rows = []
    errors = []
    seen_keys = set()
    employee_codes = {
        employee.personnel_code: employee.id
        for employee in db.query(Employee).filter(Employee.is_active.is_(True)).all()
    }
    for row_number, row in enumerate(rows, start=2):
        code = row["employee_code"].upper()
        row_errors = []
        try:
            parsed_date = date.fromisoformat(row["shift_date"])
        except ValueError:
            parsed_date = None
            row_errors.append(("shift_date", "invalid_date", "تاریخ شیفت باید با قالب YYYY-MM-DD باشد."))
        if code not in employee_codes:
            row_errors.append(("employee_code", "employee_not_found", "کارمند فعال پیدا نشد."))
        if not row["shift_name"] or not row["shift_code"]:
            row_errors.append(("shift", "missing_shift", "نام و کد شیفت الزامی است."))
        if not TIME_PATTERN.fullmatch(row["start_time"]) or not TIME_PATTERN.fullmatch(row["end_time"]):
            row_errors.append(("time", "invalid_time", "ساعت شروع و پایان باید با قالب HH:MM باشد."))
        elif time.fromisoformat(row["start_time"]) >= time.fromisoformat(row["end_time"]):
            row_errors.append(("time", "invalid_time_range", "ساعت پایان باید بعد از ساعت شروع باشد."))
        key = (code, row["shift_date"])
        if key in seen_keys:
            row_errors.append(("shift_date", "duplicate_in_file", "کارمند و تاریخ در فایل تکراری است."))
        if row_errors:
            errors.extend(_row_errors(row_number, row, row_errors))
            continue
        seen_keys.add(key)
        valid_rows.append(
            {
                **row,
                "employee_code": code,
                "employee_id": employee_codes[code],
                "shift_date": parsed_date.isoformat(),
                "start_time": time.fromisoformat(row["start_time"]).isoformat(timespec="minutes"),
                "end_time": time.fromisoformat(row["end_time"]).isoformat(timespec="minutes"),
            }
        )
    return valid_rows, errors


def _apply_employee_rows(db: Session, rows: list[dict]) -> int:
    imported = 0
    employees_by_code = {
        employee.personnel_code: employee
        for employee in db.query(Employee).filter(
            Employee.personnel_code.in_([row["employee_code"] for row in rows])
        ).all()
    }
    departments = {department.name: department for department in db.query(Department).all()}
    users_by_mobile = {
        user.mobile: user
        for user in db.query(User).filter(User.mobile.in_([row["mobile"] for row in rows])).all()
    }
    for row in rows:
        department = departments.get(row["department"])
        if department is None:
            department = Department(name=row["department"])
            db.add(department)
            db.flush()
            departments[department.name] = department
        user = users_by_mobile.get(row["mobile"])
        if user is None:
            user = User(mobile=row["mobile"], role=row["role"], is_active=True)
            db.add(user)
            db.flush()
            users_by_mobile[user.mobile] = user
        else:
            user.role = row["role"]
            user.is_active = True
        employee = employees_by_code.get(row["employee_code"])
        if employee is None:
            employee = Employee(personnel_code=row["employee_code"])
            db.add(employee)
            employees_by_code[employee.personnel_code] = employee
        employee.first_name = row["first_name"]
        employee.last_name = row["last_name"]
        employee.mobile = row["mobile"]
        employee.department_id = department.id
        employee.user_id = user.id
        employee.is_active = True
        imported += 1
    db.flush()
    supervisors = {
        employee.personnel_code: employee.id
        for employee in db.query(Employee).filter(
            Employee.personnel_code.in_(
                [row.get("supervisor_code") for row in rows if row.get("supervisor_code")]
            )
        ).all()
    }
    for row in rows:
        if row.get("supervisor_code"):
            employees_by_code[row["employee_code"]].supervisor_id = supervisors.get(row["supervisor_code"])
    return imported


def _apply_shift_rows(db: Session, rows: list[dict]) -> int:
    imported = 0
    for row in rows:
        schedule_date = date.fromisoformat(row["shift_date"])
        schedule = (
            db.query(Schedule)
            .filter(Schedule.employee_id == row["employee_id"], Schedule.date == schedule_date)
            .first()
        )
        status = row["shift_code"].upper()
        imported_values = {
            "status": status,
            "shift_name": row["shift_name"],
            "shift_code": status,
            "start_time": time.fromisoformat(row["start_time"]),
            "end_time": time.fromisoformat(row["end_time"]),
            "location": row.get("location") or None,
            "note": row.get("note") or None,
            "source": row.get("source") or "FILE_IMPORT",
            "generated_from": "IMPORT",
            "published": True,
        }
        if schedule is None:
            schedule = Schedule(
                employee_id=row["employee_id"],
                date=schedule_date,
                **imported_values,
            )
            db.add(schedule)
        else:
            for field_name, value in imported_values.items():
                setattr(schedule, field_name, value)
        imported += 1
    return imported


def _capture_employee_snapshots(db: Session, rows: list[dict]) -> list[dict]:
    snapshots = []
    for row in rows:
        employee = db.query(Employee).filter(Employee.personnel_code == row["employee_code"]).first()
        user_existed = db.query(User).filter(User.mobile == row["mobile"]).first() is not None
        department_existed = (
            db.query(Department).filter(Department.name == row["department"]).first() is not None
        )
        if employee is None:
            snapshots.append(
                {
                    "employee_code": row["employee_code"],
                    "existed": False,
                    "import_mobile": row["mobile"],
                    "import_department": row["department"],
                    "user_existed": user_existed,
                    "department_existed": department_existed,
                }
            )
            continue
        snapshots.append(
            {
                "employee_code": employee.personnel_code,
                "existed": True,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "mobile": employee.mobile,
                "department_id": employee.department_id,
                "supervisor_id": employee.supervisor_id,
                "user_id": employee.user_id,
                "is_active": employee.is_active,
                "import_mobile": row["mobile"],
                "import_department": row["department"],
                "user_existed": user_existed,
                "department_existed": department_existed,
            }
        )
    return snapshots


def _capture_shift_snapshots(db: Session, rows: list[dict]) -> list[dict]:
    snapshots = []
    for row in rows:
        schedule_date = date.fromisoformat(row["shift_date"])
        schedule = (
            db.query(Schedule)
            .filter(Schedule.employee_id == row["employee_id"], Schedule.date == schedule_date)
            .first()
        )
        if schedule is None:
            snapshots.append(
                {
                    "employee_id": row["employee_id"],
                    "date": row["shift_date"],
                    "existed": False,
                }
            )
            continue
        snapshots.append(
            {
                "employee_id": schedule.employee_id,
                "date": schedule.date.isoformat(),
                "existed": True,
                "status": schedule.status,
                "shift_name": schedule.shift_name,
                "shift_code": schedule.shift_code,
                "start_time": (
                    schedule.start_time.isoformat(timespec="minutes")
                    if schedule.start_time
                    else None
                ),
                "end_time": (
                    schedule.end_time.isoformat(timespec="minutes")
                    if schedule.end_time
                    else None
                ),
                "location": schedule.location,
                "note": schedule.note,
                "source": schedule.source,
                "generated_from": schedule.generated_from,
                "published": schedule.published,
            }
        )
    return snapshots


def _restore_employee_snapshots(db: Session, snapshots: list[dict]) -> None:
    for snapshot in reversed(snapshots):
        employee = (
            db.query(Employee)
            .filter(Employee.personnel_code == snapshot["employee_code"])
            .first()
        )
        if not snapshot["existed"]:
            if employee is not None:
                db.delete(employee)
            continue
        if employee is None:
            raise ValueError(f"کارمند هنگام بازگردانی پیدا نشد: {snapshot['employee_code']}")
        employee.first_name = snapshot["first_name"]
        employee.last_name = snapshot["last_name"]
        employee.mobile = snapshot["mobile"]
        employee.department_id = snapshot["department_id"]
        employee.supervisor_id = snapshot["supervisor_id"]
        employee.user_id = snapshot["user_id"]
        employee.is_active = snapshot["is_active"]
    db.flush()
    for snapshot in snapshots:
        if not snapshot["user_existed"]:
            user = db.query(User).filter(User.mobile == snapshot["import_mobile"]).first()
            if user is not None and db.query(Employee).filter(Employee.user_id == user.id).count() == 0:
                db.delete(user)
        if not snapshot["department_existed"]:
            department = (
                db.query(Department)
                .filter(Department.name == snapshot["import_department"])
                .first()
            )
            if (
                department is not None
                and db.query(Employee).filter(Employee.department_id == department.id).count() == 0
            ):
                db.delete(department)


def _restore_shift_snapshots(db: Session, snapshots: list[dict]) -> None:
    for snapshot in snapshots:
        schedule_date = date.fromisoformat(snapshot["date"])
        schedule = (
            db.query(Schedule)
            .filter(
                Schedule.employee_id == snapshot["employee_id"],
                Schedule.date == schedule_date,
            )
            .first()
        )
        if not snapshot["existed"]:
            if schedule is not None:
                db.delete(schedule)
            continue
        if schedule is None:
            raise ValueError("برنامه شیفت هنگام بازگردانی پیدا نشد.")
        schedule.status = snapshot["status"]
        schedule.shift_name = snapshot["shift_name"]
        schedule.shift_code = snapshot["shift_code"]
        schedule.start_time = (
            time.fromisoformat(snapshot["start_time"]) if snapshot["start_time"] else None
        )
        schedule.end_time = (
            time.fromisoformat(snapshot["end_time"]) if snapshot["end_time"] else None
        )
        schedule.location = snapshot["location"]
        schedule.note = snapshot["note"]
        schedule.source = snapshot["source"]
        schedule.generated_from = snapshot["generated_from"]
        schedule.published = snapshot["published"]


def _headers(rows: list[dict]) -> set[str]:
    return set(rows[0]) if rows else set()


def _file_error(message: str) -> dict:
    return {
        "row_number": 1,
        "field_name": None,
        "error_code": "invalid_header",
        "message": message,
        "raw_data_json": None,
    }


def _row_errors(row_number: int, row: dict, errors: list[tuple]) -> list[dict]:
    raw_data = json.dumps(row, ensure_ascii=False)
    return [
        {
            "row_number": row_number,
            "field_name": field_name,
            "error_code": error_code,
            "message": message,
            "raw_data_json": raw_data,
        }
        for field_name, error_code, message in errors
    ]


def _write_audit(db: Session, user_id: int, action: str, job: ImportJob) -> None:
    _add_audit(db, user_id, action, job)
    db.commit()


def _add_audit(db: Session, user_id: int, action: str, job: ImportJob) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            before_value=f"job_id={job.id},type={job.import_type}",
            after_value=(
                f"status={job.status},total={job.total_rows},"
                f"valid={job.valid_rows},rejected={job.rejected_rows}"
            ),
        )
    )
