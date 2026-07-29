from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.modules.employees.hr_import_service import import_hr_employees_csv
from app.seed.mvp_seed import seed_mvp_data


SAMPLE_EMPLOYEES = [
    {"personnel_code": "HR-001", "first_name": "Leila", "last_name": "Rahimi", "mobile": "09120000001", "role": "HR"},
    {"personnel_code": "SUP-001", "first_name": "Sara", "last_name": "Mohammadi", "mobile": "09120000002", "role": "SUPERVISOR"},
    {"personnel_code": "SUP-002", "first_name": "Amir", "last_name": "Karimi", "mobile": "09120000003", "role": "SUPERVISOR"},
    {"personnel_code": "SUP-003", "first_name": "Neda", "last_name": "Ebrahimi", "mobile": "09120000004", "role": "SUPERVISOR"},
    {"personnel_code": "EMP-001", "first_name": "Ali", "last_name": "Ahmadi", "mobile": "09120000005", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-002", "first_name": "Reza", "last_name": "Jafari", "mobile": "09120000006", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-003", "first_name": "Hossein", "last_name": "Moradi", "mobile": "09120000007", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-004", "first_name": "Fatemeh", "last_name": "Yazdani", "mobile": "09120000008", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-005", "first_name": "Maryam", "last_name": "Sadeghi", "mobile": "09120000009", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-006", "first_name": "Zahra", "last_name": "Ghasemi", "mobile": "09120000010", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-007", "first_name": "Sina", "last_name": "Hosseini", "mobile": "09120000011", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-008", "first_name": "Elham", "last_name": "Farhadi", "mobile": "09120000012", "role": "EMPLOYEE"},
    {"personnel_code": "EMP-009", "first_name": "Mehdi", "last_name": "Ranjbar", "mobile": "09120000013", "role": "EMPLOYEE"},
    {"personnel_code": "IT-001", "first_name": "Pouya", "last_name": "Karimi", "mobile": "09120000014", "role": "ADMIN"},
]


def write_sample_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["personnel_code", "first_name", "last_name", "mobile", "role"])
        writer.writeheader()
        writer.writerows(SAMPLE_EMPLOYEES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed sample employees into the database.")
    parser.add_argument("--seed-base", action="store_true", help="Seed the base MVP data first.")
    parser.add_argument("--default-department", default="Operations")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        base_result = seed_mvp_data(db) if args.seed_base else None
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8", newline="") as temp_file:
            temp_path = Path(temp_file.name)
        write_sample_csv(temp_path)
        try:
            result = import_hr_employees_csv(
                db,
                temp_path,
                default_department_name=args.default_department,
                audit_user_id=base_result["supervisor_user_id"] if base_result else None,
            )
        finally:
            temp_path.unlink(missing_ok=True)
    finally:
        db.close()

    output = {"seed_base": base_result, "import": result}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
