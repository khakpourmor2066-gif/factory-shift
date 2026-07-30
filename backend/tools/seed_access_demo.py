from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.modules.access_requests.model import AccessRequest
from app.modules.employees.hr_import_service import import_hr_employees_csv
from app.modules.employees.model import Employee
from app.seed.mvp_seed import seed_active_employee_schedules, seed_mvp_data


DEMO_CSV = """personnel_code,first_name,last_name,mobile,role
HR-001,Leila,Rahimi,09120000001,HR
SUP-001,Sara,Mohammadi,09120000002,SUPERVISOR
SUP-002,Amir,Karimi,09120000003,SUPERVISOR
SUP-003,Neda,Ebrahimi,09120000004,SUPERVISOR
EMP-001,Ali,Ahmadi,09120000005,EMPLOYEE
EMP-002,Reza,Jafari,09120000006,EMPLOYEE
EMP-003,Hossein,Moradi,09120000007,EMPLOYEE
EMP-004,Fatemeh,Yazdani,09120000008,EMPLOYEE
EMP-005,Maryam,Sadeghi,09120000009,EMPLOYEE
EMP-006,Zahra,Ghasemi,09120000010,EMPLOYEE
EMP-007,Sina,Hosseini,09120000011,EMPLOYEE
EMP-008,Elham,Farhadi,09120000012,EMPLOYEE
EMP-009,Mehdi,Ranjbar,09120000013,EMPLOYEE
IT-001,Pouya,Karimi,09120000014,ADMIN
"""


def ensure_demo_access_requests(db):
    demo_rows = [
        ("bale", "9001", "ثبت 09120000006 EMP-002", "pending", 1),
        ("bale", "9002", "ثبت 09120000007 EMP-003", "pending", 2),
        ("bale", "9003", "ثبت 09120009999 EMP-999", "pending", 1),
        ("bale", "9004", "ثبت 09120000005 EMP-001", "approved", 1),
        ("bale", "9005", "ثبت 09120000005 EMP-001", "rejected", 1),
    ]
    created = 0
    for platform, messenger_user_id, latest_text, status, request_count in demo_rows:
        existing = (
            db.query(AccessRequest)
            .filter(AccessRequest.platform == platform)
            .filter(AccessRequest.messenger_user_id == messenger_user_id)
            .filter(AccessRequest.status == status)
            .first()
        )
        if existing is None:
            db.add(
                AccessRequest(
                    platform=platform,
                    messenger_user_id=messenger_user_id,
                    latest_text=latest_text,
                    status=status,
                    request_count=request_count,
                )
            )
            created += 1
    db.commit()
    return created


def assign_demo_supervisors(db):
    groups = {
        "SUP-001": ["EMP-001", "EMP-002", "EMP-003"],
        "SUP-002": ["EMP-004", "EMP-005", "EMP-006"],
        "SUP-003": ["EMP-007", "EMP-008", "EMP-009"],
    }
    updated = 0
    for supervisor_code, employee_codes in groups.items():
        supervisor = (
            db.query(Employee)
            .filter(Employee.personnel_code == supervisor_code)
            .one()
        )
        employees = (
            db.query(Employee)
            .filter(Employee.personnel_code.in_(employee_codes))
            .all()
        )
        for employee in employees:
            if employee.supervisor_id != supervisor.id:
                employee.supervisor_id = supervisor.id
                updated += 1
    db.commit()
    return updated


def next_month_end(start_date: date) -> date:
    if start_date.month == 12:
        month_after_next = date(start_date.year + 1, 2, 1)
    elif start_date.month == 11:
        month_after_next = date(start_date.year + 1, 1, 1)
    else:
        month_after_next = date(start_date.year, start_date.month + 2, 1)
    return month_after_next - timedelta(days=1)


def main() -> int:
    db = SessionLocal()
    try:
        base_result = seed_mvp_data(db)
        hr_csv = Path(__file__).with_name("seed_access_demo_hr.csv")
        hr_csv.write_text(DEMO_CSV, encoding="utf-8")
        hr_result = import_hr_employees_csv(db, hr_csv, audit_user_id=base_result["supervisor_user_id"])
        supervisor_links_updated = assign_demo_supervisors(db)
        schedule_start = date.today().replace(day=1)
        schedule_result = seed_active_employee_schedules(
            db,
            start_date=schedule_start,
            end_date=next_month_end(schedule_start),
        )
        request_count = ensure_demo_access_requests(db)
    finally:
        db.close()

    output = {
        "base": base_result,
        "hr": hr_result,
        "supervisor_links_updated": supervisor_links_updated,
        "schedules": schedule_result,
        "access_requests_created": request_count,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
