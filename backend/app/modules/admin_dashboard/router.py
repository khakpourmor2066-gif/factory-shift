from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user, require_roles
from app.modules.access_requests.service import get_access_request_report
from app.modules.change_management.services.change_management_service import get_audit_log_report
from app.modules.users.model import User
from app.modules.webhook_logs.service import get_webhook_log_report

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_roles(current_user, {"SUPERVISOR", "ADMIN", "HR"})
    access_report = get_access_request_report(db)
    webhook_report = get_webhook_log_report(db)
    audit_report = get_audit_log_report(db)

    access_counts = access_report["counts"]
    webhook_counts = webhook_report["counts"]
    audit_counts = audit_report["counts"]
    latest_requests = "".join(
        f"<li>#{item.id} · {escape(item.messenger_user_id)} · {escape(item.status)} · {item.request_count}</li>"
        for item in access_report["latest"]
    )
    latest_logs = "".join(
        f"<li>#{item.id} · {escape(item.platform)} · {escape(item.event_type)} · {escape(item.response_status or '-')}</li>"
        for item in webhook_report["latest"]
    )
    latest_audits = "".join(
        f"<li>#{item.id} · user:{item.user_id} · {escape(item.action)} · {escape(item.after_value or '-')}</li>"
        for item in audit_report["latest"]
    )
    top_audit_actions = "".join(
        f"<li>{escape(action)}: {count}</li>"
        for action, count in sorted(audit_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    )

    html = f"""
    <html lang="fa" dir="rtl">
      <head>
        <meta charset="utf-8" />
        <title>Admin Dashboard</title>
        <style>
          body {{ font-family: sans-serif; margin: 24px; line-height: 1.8; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
          .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 16px; }}
          h1, h2 {{ margin: 0 0 12px 0; }}
          ul {{ padding-right: 20px; }}
        </style>
      </head>
      <body>
        <h1>داشبورد مدیریتی</h1>
        <div class="grid">
          <div class="card">
            <h2>درخواست‌ها</h2>
            <div>کل: {access_report["total"]}</div>
            <div>در انتظار: {access_counts.get("pending", 0)}</div>
            <div>تایید شده: {access_counts.get("approved", 0)}</div>
            <div>رد شده: {access_counts.get("rejected", 0)}</div>
          </div>
          <div class="card">
            <h2>لاگ‌های وبهوک</h2>
            <div>کل: {webhook_report["total"]}</div>
            <div>ورودی: {webhook_counts.get("incoming", 0)}</div>
            <div>خروجی: {webhook_counts.get("outgoing", 0)}</div>
            <div>ارسال موفق: {webhook_counts.get("sent", 0)}</div>
            <div>ارسال ناموفق: {webhook_counts.get("failed", 0)}</div>
          </div>
          <div class="card">
            <h2>حسابرسی</h2>
            <div>کل: {audit_report["total"]}</div>
            <ul>{top_audit_actions or "<li>موردی وجود ندارد</li>"}</ul>
          </div>
        </div>
        <div class="grid" style="margin-top:16px;">
          <div class="card">
            <h2>آخرین درخواست‌ها</h2>
            <ul>{latest_requests or "<li>موردی وجود ندارد</li>"}</ul>
          </div>
          <div class="card">
            <h2>آخرین لاگ‌ها</h2>
            <ul>{latest_logs or "<li>موردی وجود ندارد</li>"}</ul>
          </div>
          <div class="card">
            <h2>آخرین رویدادهای حسابرسی</h2>
            <ul>{latest_audits or "<li>موردی وجود ندارد</li>"}</ul>
          </div>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
