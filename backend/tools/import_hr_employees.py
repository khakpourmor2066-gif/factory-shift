import argparse

from app.database.connection import SessionLocal
from app.modules.employees.hr_import_service import import_hr_employees_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Import HR employees from CSV")
    parser.add_argument("--file", required=True, help="CSV file path")
    parser.add_argument("--department", default="Operations", help="Default department name")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = import_hr_employees_csv(db, args.file, args.department)
    finally:
        db.close()

    print(f"created={result['created']} updated={result['updated']} errors={len(result['errors'])}")
    for error in result["errors"]:
        print(f"row={error['row']} error={error['error']}")


if __name__ == "__main__":
    main()
