from fastapi import APIRouter

from app.modules.attendance.router import router as attendance_router
from app.modules.auth_tokens.router import router as auth_tokens_router
from app.modules.access_requests.router import router as access_requests_router
from app.modules.admin_dashboard.router import router as admin_dashboard_router
from app.modules.bot_adapter.router import router as bot_adapter_router
from app.modules.change_management.router import router as change_management_router
from app.modules.departments.router import router as departments_router
from app.modules.employee_view.router import router as employee_view_router
from app.modules.employees.router import router as employees_router
from app.modules.data_imports.router import router as data_imports_router
from app.modules.reports.router import router as reports_router
from app.modules.schedule_generation.router import router as schedule_generation_router
from app.modules.shifts.router import router as shifts_router
from app.modules.supervisor_view.router import router as supervisor_view_router
from app.modules.users.router import router as users_router
from app.modules.webhook_logs.router import router as webhook_logs_router

api_router = APIRouter()
api_router.include_router(auth_tokens_router)
api_router.include_router(users_router)
api_router.include_router(departments_router)
api_router.include_router(employees_router)
api_router.include_router(data_imports_router)
api_router.include_router(shifts_router)
api_router.include_router(schedule_generation_router)
api_router.include_router(employee_view_router)
api_router.include_router(supervisor_view_router)
api_router.include_router(bot_adapter_router)
api_router.include_router(access_requests_router)
api_router.include_router(admin_dashboard_router)
api_router.include_router(webhook_logs_router)
api_router.include_router(change_management_router)
api_router.include_router(attendance_router)
api_router.include_router(reports_router)
