from pathlib import Path
from types import SimpleNamespace

from app.modules.departments.model import Department
from app.modules.employees.model import Employee
from app.modules.users.model import User
from app.modules.employees import hr_import_service


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self):
        self.objects = []
        self.audit_user = SimpleNamespace(id=1)
        self.department = None
        self.user = None
        self.employee = None

    def query(self, model):
        if model is User:
            return FakeQuery(self.audit_user if self.user is None else self.user)
        if model is Department:
            return FakeQuery(self.department)
        if model is Employee:
            return FakeQuery(self.employee)
        return FakeQuery(None)

    def add(self, obj):
        self.objects.append(obj)
        if isinstance(obj, Department):
            self.department = obj
        elif isinstance(obj, User):
            self.user = obj
        elif isinstance(obj, Employee):
            self.employee = obj

    def flush(self):
        for index, obj in enumerate(self.objects, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = index

    def commit(self):
        return None

    def refresh(self, obj):
        return None


def test_hr_import_writes_audit_log(tmp_path, monkeypatch):
    csv_path = tmp_path / "employees.csv"
    csv_path.write_text(
        "personnel_code,first_name,last_name,mobile,role\n"
        "EMP-001,Ali,Worker,09120000001,EMPLOYEE\n",
        encoding="utf-8",
    )

    captured_audit = []
    monkeypatch.setattr(hr_import_service, "create_audit_log", lambda db, payload: captured_audit.append(payload))

    session = FakeSession()
    result = hr_import_service.import_hr_employees_csv(session, csv_path)

    assert result["created"] == 1
    assert result["updated"] == 0
    assert captured_audit
    assert captured_audit[0].action == "hr_employees_imported"
    assert captured_audit[0].user_id == 1
