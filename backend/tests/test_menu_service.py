from app.modules.bot_adapter.services.menu_service import get_menu_for_role


def test_employee_menu():
    menu = get_menu_for_role("EMPLOYEE")

    assert "برنامه من" in menu
    assert "افراد روز" not in menu
    assert "عملیات" not in menu
    assert "خروج از حساب" in menu


def test_supervisor_menu():
    menu = get_menu_for_role("SUPERVISOR")

    assert "افراد روز" in menu
    assert "درخواست‌ها" not in menu
    assert "عملیات" not in menu
    assert "خروج از حساب" in menu


def test_management_menus_include_access_operations():
    for role in ("HR", "ADMIN"):
        menu = get_menu_for_role(role)

        assert "درخواست‌ها" in menu
        assert "عملیات" in menu
        assert "خروج از حساب" in menu
