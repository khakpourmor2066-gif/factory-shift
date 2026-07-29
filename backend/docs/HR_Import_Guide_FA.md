# راهنمای واردسازی کارکنان برای منابع انسانی

## هدف

کاربر دارای نقش `HR` می‌تواند فایل کارکنان را ابتدا پیش‌نمایش کند، خطاها را ببیند و
پس از اطمینان آن را تأیید کند.

## ستون‌های لازم

```text
employee_code,first_name,last_name,mobile,department,role
```

ستون `supervisor_code` اختیاری است. نقش باید یکی از `EMPLOYEE`، `SUPERVISOR`،
`HR` یا `ADMIN` باشد.

## روش اجرا

```bash
python tools/import_data.py employees.xlsx --type employees --user-id <HR_USER_ID>
```

در صورت درست بودن پیش‌نمایش:

```bash
python tools/import_data.py employees.xlsx --type employees --user-id <HR_USER_ID> --confirm
```

هر خطا با شماره ردیف، نام فیلد و دلیل رد ذخیره می‌شود. اگر نتیجه تأییدشده اشتباه
بود، کاربر مجاز می‌تواند endpoint بازگردانی همان job را اجرا کند.
