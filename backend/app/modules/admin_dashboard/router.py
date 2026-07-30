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
    schedule_generator_link = (
        '<p><a href="/admin/schedule-generator">تولید و انتشار برنامه شیفت</a></p>'
        if current_user.role in {"HR", "ADMIN"}
        else ""
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
        <p><a href="/admin/imports">ورود کارکنان و برنامه شیفت</a></p>
        {schedule_generator_link}
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


@router.get("/imports", response_class=HTMLResponse, include_in_schema=False)
def import_dashboard_endpoint():
    html = """
    <html lang="fa" dir="rtl">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>ورود اطلاعات Factory Shift</title>
        <style>
          body { font-family: sans-serif; margin: 24px; line-height: 1.8; background: #f6f7f9; }
          main { max-width: 900px; margin: auto; }
          .card { background: white; border: 1px solid #ddd; border-radius: 12px; padding: 18px; margin: 14px 0; }
          label { display: block; margin: 10px 0 4px; font-weight: bold; }
          input, select, button { font: inherit; padding: 9px; margin: 3px; }
          input[type="password"], input[type="file"], select { width: min(95%, 580px); }
          button { cursor: pointer; border: 1px solid #aaa; border-radius: 8px; }
          button.primary { background: #087f5b; color: white; border-color: #087f5b; }
          button.danger { background: #c92a2a; color: white; border-color: #c92a2a; }
          pre { direction: ltr; text-align: left; white-space: pre-wrap; background: #111; color: #eee; padding: 14px; border-radius: 8px; }
          .hint { color: #555; }
        </style>
      </head>
      <body>
        <main>
          <h1>ورود کارکنان و برنامه شیفت</h1>
          <p class="hint">توکن فقط در حافظه همین صفحه استفاده می‌شود و ذخیره نمی‌شود.</p>
          <section class="card">
            <label for="token">Bearer Token</label>
            <input id="token" type="password" autocomplete="off" />
            <label for="importType">نوع فایل</label>
            <select id="importType">
              <option value="employees">کارکنان منابع انسانی</option>
              <option value="shifts">برنامه شیفت</option>
            </select>
            <label for="file">فایل CSV یا XLSX</label>
            <input id="file" type="file" accept=".csv,.xlsx" />
            <div>
              <button class="primary" id="preview">پیش‌نمایش</button>
              <button id="template">دریافت قالب</button>
            </div>
          </section>
          <section class="card">
            <div>شناسه job: <strong id="jobId">-</strong></div>
            <button class="primary" id="confirm" disabled>تأیید</button>
            <button class="danger" id="reject" disabled>رد</button>
            <button id="rollback" disabled>بازگردانی</button>
            <pre id="result">هنوز فایلی بررسی نشده است.</pre>
          </section>
        </main>
        <script>
          const tokenInput = document.getElementById("token");
          const typeInput = document.getElementById("importType");
          const fileInput = document.getElementById("file");
          const result = document.getElementById("result");
          const jobIdOutput = document.getElementById("jobId");
          const confirmButton = document.getElementById("confirm");
          const rejectButton = document.getElementById("reject");
          const rollbackButton = document.getElementById("rollback");
          let currentJobId = null;

          function headers() {
            return { "Authorization": `Bearer ${tokenInput.value.trim()}` };
          }

          function show(payload) {
            const job = payload.job || (payload.id && payload.import_type ? payload : null);
            if (job) {
              const errors = payload.errors || [];
              const lines = [
                `وضعیت: ${job.status}`,
                `کل ردیف‌ها: ${job.total_rows}`,
                `ردیف‌های معتبر: ${job.valid_rows}`,
                `ردیف‌های واردشده: ${job.imported_rows}`,
                `ردیف‌های ردشده: ${job.rejected_rows}`
              ];
              for (const error of errors) {
                lines.push(`ردیف ${error.row_number} - ${error.field_name || "فایل"}: ${error.message}`);
              }
              result.textContent = lines.join("\\n");
              return;
            }
            result.textContent = JSON.stringify(payload, null, 2);
          }

          async function request(path, options = {}) {
            const response = await fetch(path, options);
            const payload = await response.json();
            show(payload);
            if (!response.ok) throw new Error(payload.detail || "request failed");
            return payload;
          }

          document.getElementById("preview").addEventListener("click", async () => {
            if (!tokenInput.value.trim() || !fileInput.files.length) {
              show({error: "توکن و فایل الزامی است."});
              return;
            }
            const form = new FormData();
            form.append("file", fileInput.files[0]);
            try {
              const payload = await request(`/imports/${typeInput.value}/preview`, {
                method: "POST", headers: headers(), body: form
              });
              currentJobId = payload.job.id;
              jobIdOutput.textContent = currentJobId;
              confirmButton.disabled = false;
              rejectButton.disabled = false;
              rollbackButton.disabled = true;
            } catch (_) {}
          });

          confirmButton.addEventListener("click", async () => {
            try {
              await request(`/imports/${currentJobId}/confirm`, {method: "POST", headers: headers()});
              confirmButton.disabled = true;
              rejectButton.disabled = true;
              rollbackButton.disabled = false;
            } catch (_) {}
          });

          rejectButton.addEventListener("click", async () => {
            try {
              await request(`/imports/${currentJobId}/reject`, {method: "POST", headers: headers()});
              confirmButton.disabled = true;
              rejectButton.disabled = true;
            } catch (_) {}
          });

          rollbackButton.addEventListener("click", async () => {
            try {
              await request(`/imports/${currentJobId}/rollback`, {method: "POST", headers: headers()});
              rollbackButton.disabled = true;
            } catch (_) {}
          });

          document.getElementById("template").addEventListener("click", async () => {
            try {
              const payload = await request(`/imports/templates/${typeInput.value}`, {headers: headers()});
              const blob = new Blob([payload.content], {type: payload.content_type});
              const link = document.createElement("a");
              link.href = URL.createObjectURL(blob);
              link.download = payload.filename;
              link.click();
              URL.revokeObjectURL(link.href);
            } catch (_) {}
          });
        </script>
      </body>
    </html>
    """
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'"
            ),
        },
    )


@router.get("/schedule-generator", response_class=HTMLResponse, include_in_schema=False)
def schedule_generator_dashboard_endpoint():
    html = """
    <html lang="fa" dir="rtl">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>تولید برنامه شیفت</title>
        <style>
          body { font-family: sans-serif; margin: 24px; line-height: 1.8; background: #f6f7f9; color: #222; }
          main { max-width: 1050px; margin: auto; }
          .card { background: white; border: 1px solid #ddd; border-radius: 12px; padding: 18px; margin: 14px 0; }
          .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
          label { display: block; margin: 8px 0 4px; font-weight: bold; }
          input, select, button { font: inherit; padding: 9px; box-sizing: border-box; }
          input, select { width: 100%; }
          button { cursor: pointer; border: 1px solid #aaa; border-radius: 8px; margin: 4px; }
          button:disabled { cursor: not-allowed; opacity: .5; }
          button.primary { background: #087f5b; color: white; border-color: #087f5b; }
          button.publish { background: #1864ab; color: white; border-color: #1864ab; }
          button.danger { background: #c92a2a; color: white; border-color: #c92a2a; }
          .hint { color: #555; }
          .summary { display: flex; flex-wrap: wrap; gap: 10px; }
          .badge { background: #edf2ff; border-radius: 999px; padding: 5px 12px; }
          table { width: 100%; border-collapse: collapse; margin-top: 12px; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
          th { background: #f1f3f5; }
          #message { white-space: pre-wrap; border-radius: 8px; padding: 10px; background: #f8f9fa; }
          .error { color: #c92a2a; }
        </style>
      </head>
      <body>
        <main>
          <p><a href="/admin/dashboard">بازگشت به داشبورد</a> · <a href="/admin/imports">ورود فایل</a></p>
          <h1>تولید و انتشار برنامه شیفت</h1>
          <p class="hint">این صفحه فقط با توکن نقش HR یا Admin کار می‌کند. توکن در مرورگر ذخیره نمی‌شود.</p>
          <section class="card">
            <label for="token">Bearer Token</label>
            <input id="token" type="password" autocomplete="off" />
            <button class="primary" id="loadOptions">دریافت کارکنان و الگوها</button>
          </section>
          <section class="card">
            <div class="grid">
              <div>
                <label for="employee">کارمند</label>
                <select id="employee" disabled></select>
              </div>
              <div>
                <label for="assignment">الگوی اختصاص‌یافته</label>
                <select id="assignment" disabled></select>
              </div>
              <div>
                <label for="fromDate">از تاریخ</label>
                <input id="fromDate" type="date" />
              </div>
              <div>
                <label for="toDate">تا تاریخ</label>
                <input id="toDate" type="date" />
              </div>
            </div>
            <button class="primary" id="preview" disabled>مشاهده پیش‌نمایش</button>
          </section>
          <section class="card">
            <div class="summary">
              <span class="badge">Job: <strong id="jobId">-</strong></span>
              <span class="badge">وضعیت: <strong id="status">-</strong></span>
              <span class="badge">کل بازه: <strong id="totalDays">0</strong></span>
              <span class="badge">روز موجود: <strong id="existingDays">0</strong></span>
              <span class="badge">روز قابل تکمیل: <strong id="missingDays">0</strong></span>
            </div>
            <p id="message">هنوز پیش‌نمایشی ایجاد نشده است.</p>
            <div>
              <button class="primary" id="confirm" disabled>تأیید و ذخیره پیش‌نویس</button>
              <button class="publish" id="publish" disabled>انتشار برنامه</button>
              <button class="danger" id="cancel" disabled>لغو</button>
            </div>
            <table>
              <thead><tr><th>تاریخ</th><th>وضعیت پیشنهادی</th></tr></thead>
              <tbody id="previewRows"><tr><td colspan="2">موردی وجود ندارد</td></tr></tbody>
            </table>
          </section>
        </main>
        <script>
          const tokenInput = document.getElementById("token");
          const employeeInput = document.getElementById("employee");
          const assignmentInput = document.getElementById("assignment");
          const fromDateInput = document.getElementById("fromDate");
          const toDateInput = document.getElementById("toDate");
          const previewButton = document.getElementById("preview");
          const confirmButton = document.getElementById("confirm");
          const publishButton = document.getElementById("publish");
          const cancelButton = document.getElementById("cancel");
          const message = document.getElementById("message");
          let employees = [];
          let currentJobId = null;

          function headers() {
            return {
              "Authorization": `Bearer ${tokenInput.value.trim()}`,
              "Content-Type": "application/json"
            };
          }

          function setDefaultDates() {
            const today = new Date();
            const nextWeek = new Date(today);
            nextWeek.setDate(today.getDate() + 6);
            fromDateInput.value = today.toISOString().slice(0, 10);
            toDateInput.value = nextWeek.toISOString().slice(0, 10);
          }

          function showError(error) {
            message.className = "error";
            message.textContent = error.message || String(error);
          }

          async function request(path, options = {}) {
            const response = await fetch(path, options);
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.detail || "درخواست ناموفق بود.");
            return payload;
          }

          function updateAssignments() {
            const employee = employees.find(item => String(item.id) === employeeInput.value);
            assignmentInput.innerHTML = "";
            for (const assignment of (employee?.assignments || [])) {
              const option = document.createElement("option");
              option.value = assignment.id;
              const endDate = assignment.end_date || "بدون پایان";
              option.textContent = `${assignment.pattern_name} · ${assignment.start_date} تا ${endDate}`;
              assignmentInput.appendChild(option);
            }
            assignmentInput.disabled = !assignmentInput.options.length;
            previewButton.disabled = assignmentInput.disabled;
          }

          function renderJob(job) {
            currentJobId = job.id;
            document.getElementById("jobId").textContent = job.id;
            document.getElementById("status").textContent = job.status;
            document.getElementById("totalDays").textContent = job.total_days;
            document.getElementById("existingDays").textContent = job.existing_days;
            document.getElementById("missingDays").textContent = job.missing_days;
            const rows = document.getElementById("previewRows");
            rows.innerHTML = "";
            if (!job.preview.length) {
              rows.innerHTML = '<tr><td colspan="2">تمام روزهای این بازه از قبل برنامه دارند.</td></tr>';
            } else {
              for (const item of job.preview) {
                const row = document.createElement("tr");
                const dateCell = document.createElement("td");
                const statusCell = document.createElement("td");
                dateCell.textContent = item.date;
                statusCell.textContent = item.status;
                row.appendChild(dateCell);
                row.appendChild(statusCell);
                rows.appendChild(row);
              }
            }
            const pending = job.status === "PENDING";
            confirmButton.disabled = !pending;
            cancelButton.disabled = !pending;
            publishButton.disabled = !["PENDING", "CONFIRMED"].includes(job.status);
            message.className = "";
            message.textContent = job.status === "PENDING"
              ? "پیش‌نمایش آماده است. ذخیره پیش‌نویس، انتشار مستقیم یا لغو را انتخاب کنید."
              : `عملیات با وضعیت ${job.status} تکمیل شد. تعداد برنامه ایجادشده: ${job.created_schedules}`;
          }

          document.getElementById("loadOptions").addEventListener("click", async () => {
            if (!tokenInput.value.trim()) return showError(new Error("توکن الزامی است."));
            try {
              const payload = await request("/schedule-generation/options", {headers: headers()});
              employees = payload.employees;
              employeeInput.innerHTML = "";
              for (const employee of employees) {
                const option = document.createElement("option");
                option.value = employee.id;
                option.textContent = `${employee.personnel_code} · ${employee.full_name}`;
                employeeInput.appendChild(option);
              }
              employeeInput.disabled = !employees.length;
              updateAssignments();
              message.className = "";
              message.textContent = employees.length
                ? "کارمند، الگو و بازه را انتخاب کنید."
                : "هیچ کارمند دارای Assignment فعال پیدا نشد.";
            } catch (error) { showError(error); }
          });

          employeeInput.addEventListener("change", updateAssignments);

          previewButton.addEventListener("click", async () => {
            const employeeId = Number(employeeInput.value);
            const assignmentId = Number(assignmentInput.value);
            if (!employeeId || !assignmentId || !fromDateInput.value || !toDateInput.value) {
              return showError(new Error("انتخاب کارمند، الگو و بازه تاریخ الزامی است."));
            }
            try {
              const job = await request("/schedule-generation/preview", {
                method: "POST",
                headers: headers(),
                body: JSON.stringify({
                  employee_id: employeeId,
                  assignment_id: assignmentId,
                  from_date: fromDateInput.value,
                  to_date: toDateInput.value
                })
              });
              renderJob(job);
            } catch (error) { showError(error); }
          });

          async function transition(action) {
            if (!currentJobId) return;
            try {
              const job = await request(`/schedule-generation/${currentJobId}/${action}`, {
                method: "POST",
                headers: headers()
              });
              renderJob(job);
            } catch (error) { showError(error); }
          }

          confirmButton.addEventListener("click", () => transition("confirm"));
          publishButton.addEventListener("click", () => transition("publish"));
          cancelButton.addEventListener("click", () => transition("cancel"));
          setDefaultDates();
        </script>
      </body>
    </html>
    """
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'"
            ),
        },
    )
