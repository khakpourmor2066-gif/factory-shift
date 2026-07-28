EMPLOYEE = "EMPLOYEE"
SUPERVISOR = "SUPERVISOR"
HR = "HR"
ADMIN = "ADMIN"

MANAGEMENT_ROLES = {HR, ADMIN}
SUPERVISOR_ROLES = {SUPERVISOR, HR, ADMIN}


def can_view_own_schedule(role: str) -> bool:
    return role in {EMPLOYEE, HR, ADMIN}


def can_view_supervisor_schedule(role: str) -> bool:
    return role in SUPERVISOR_ROLES
