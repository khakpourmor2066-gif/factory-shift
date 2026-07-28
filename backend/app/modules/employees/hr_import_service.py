import csv
from pathlib import Path

from sqlalchemy.orm import Session

from app.modules.access_requests.service import normalize_mobile
from app.modules.change_management.schemas.change_management import AuditLogCreate
from app.modules.change_management.services.change_management_service import create_audit_log
from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.users.model import User


REQUIRED_COLUMNS = {"personnel_code", "first_name", "last_name", "mobile"}


def import_hr_employees_csv(
    db: Session,
    csv_path: str | Path,
    default_department_name: str = "Operations",
    audit_user_id: int | None = None,
) -> dict:
    path = Path(csv_path)
    department = _get_or_create_department(db, default_department_name)
    created = 0
    updated = 0
    errors: list[dict] = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            return {
                "created": 0,
                "updated": 0,
                "errors": [{"row": 0, "error": f"missing columns: {', '.join(sorted(missing_columns))}"}],
            }

        for row_number, row in enumerate(reader, start=2):
            personnel_code = (row.get("personnel_code") or "").strip()
            first_name = (row.get("first_name") or "").strip()
            last_name = (row.get("last_name") or "").strip()
            mobile = normalize_mobile(row.get("mobile") or "")
            role = (row.get("role") or "EMPLOYEE").strip().upper()

            if not personnel_code or not first_name or not last_name or not mobile:
                errors.append({"row": row_number, "error": "required field is empty"})
                continue
            if not mobile.startswith("09") or len(mobile) != 11:
                errors.append({"row": row_number, "error": "invalid mobile"})
                continue
            if role not in {"EMPLOYEE", "SUPERVISOR", "HR", "ADMIN"}:
                errors.append({"row": row_number, "error": "invalid role"})
                continue

            user = _get_or_create_user_by_mobile(db, mobile, role)
            employee = db.query(Employee).filter(Employee.personnel_code == personnel_code).first()
            if employee is None:
                employee = Employee(
                    personnel_code=personnel_code,
                    first_name=first_name,
                    last_name=last_name,
                    mobile=mobile,
                    department_id=department.id,
                    user_id=user.id,
                    is_active=True,
                )
                db.add(employee)
                created += 1
            else:
                employee.first_name = first_name
                employee.last_name = last_name
                employee.mobile = mobile
                employee.department_id = department.id
                employee.user_id = user.id
                employee.is_active = True
                updated += 1

    db.commit()
    actor_user_id = audit_user_id or _get_audit_user_id(db)
    if actor_user_id is not None:
        create_audit_log(
            db,
            AuditLogCreate(
                user_id=actor_user_id,
                action="hr_employees_imported",
                before_value=f"created={created},updated={updated}",
                after_value=f"errors={len(errors)}",
            ),
        )
    return {"created": created, "updated": updated, "errors": errors}


def _get_or_create_department(db: Session, name: str) -> Department:
    department = db.query(Department).filter(Department.name == name).first()
    if department is None:
        department = Department(name=name)
        db.add(department)
        db.flush()
    return department


def _get_or_create_user_by_mobile(db: Session, mobile: str, role: str) -> User:
    user = db.query(User).filter(User.mobile == mobile).first()
    if user is None:
        user = User(mobile=mobile, role=role, messenger_user_id=None, is_active=True)
        db.add(user)
        db.flush()
    else:
        user.role = role
        user.is_active = True
    return user


def _get_audit_user_id(db: Session) -> int | None:
    user = db.query(User).first()
    return user.id if user is not None else None
