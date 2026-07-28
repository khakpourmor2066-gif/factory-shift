class PermissionError(Exception):
    pass


def ensure_role(user_role: str, allowed_roles: set[str]) -> None:
    if user_role not in allowed_roles:
        raise PermissionError(f"Role {user_role} is not allowed.")
