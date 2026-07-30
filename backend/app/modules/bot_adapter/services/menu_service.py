from app.modules.bot_adapter.menu import EMPLOYEE_MENU, SUPERVISOR_MENU


def get_menu_for_role(role: str) -> list[str]:
    if role in {"HR", "ADMIN"}:
        return [
            "برنامه شیفت من",
            "مشاهده افراد یک روز",
            "انتخاب ماه",
            "انتخاب تاریخ",
            "درخواست‌ها",
            "عملیات",
            "تولید برنامه",
            "راهنما",
            "خروج از حساب",
        ]
    if role == "SUPERVISOR":
        return SUPERVISOR_MENU
    return EMPLOYEE_MENU
