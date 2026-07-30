from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.modules.access_requests.model import AccessRequest
from app.modules.employees.hr_import_service import import_hr_employees_csv
from app.seed.mvp_seed import seed_mvp_data


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


def main() -> int:
    db = SessionLocal()
    try:
        base_result = seed_mvp_data(db)
        hr_csv = Path(__file__).with_name("seed_access_demo_hr.csv")
        hr_csv.write_text(DEMO_CSV, encoding="utf-8")
        hr_result = import_hr_employees_csv(db, hr_csv, audit_user_id=base_result["supervisor_user_id"])
        request_count = ensure_demo_access_requests(db)
    finally:
        db.close()

    output = {
        "base": base_result,
        "hr": hr_result,
        "access_requests_created": request_count,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
