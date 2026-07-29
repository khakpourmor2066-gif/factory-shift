from pathlib import Path

from tools.import_data import build_parser


def test_import_data_parser_accepts_employee_file():
    args = build_parser().parse_args(
        ["employees.csv", "--type", "employees", "--user-id", "12", "--confirm"]
    )

    assert args.file == Path("employees.csv")
    assert args.type == "employees"
    assert args.user_id == 12
    assert args.confirm is True
