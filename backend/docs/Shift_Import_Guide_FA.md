# راهنمای واردسازی شیفت برای مدیر شیفت

## هدف

کاربر دارای نقش `SUPERVISOR` می‌تواند برنامه روزانه یا ماهانه را از فایل CSV یا
Excel وارد کند. هر ردیف باید به یک کد کارمندی فعال متصل شود.

## ستون‌های لازم

```text
employee_code,shift_date,shift_name,shift_code,start_time,end_time
```

قالب تاریخ `YYYY-MM-DD` و قالب ساعت `HH:MM` است. ترکیب کد کارمندی و تاریخ نباید
در یک فایل تکرار شود.

## روش اجرا

```bash
python tools/import_data.py shifts.csv --type shifts --user-id <SUPERVISOR_USER_ID>
```

پس از بررسی پیش‌نمایش:

```bash
python tools/import_data.py shifts.csv --type shifts --user-id <SUPERVISOR_USER_ID> --confirm
```

تأیید فایل، برنامه‌های همان روز را ایجاد یا به‌روزرسانی و برای نمایش در بات منتشر
می‌کند. rollback وضعیت قبلی برنامه را از snapshot همان import بازیابی می‌کند.
