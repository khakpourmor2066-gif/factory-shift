# راهنمای تست ترکیبی بله

## هدف

تست ربات در دو لایه انجام می‌شود:

1. تست پروتکل webhook برای منطق، دیتابیس و ارسال پیام.
2. تست رابط کاربری Bale Web با حساب آزمایشی و Chrome DevTools MCP.

## تست پروتکل

ابزار `tools/bale_protocol_e2e.py` سه مرحله زیر را اجرا می‌کند:

1. ارسال شماره موبایل؛
2. ارسال کد کارمندی؛
3. ارسال `/start`.

این ابزار به‌صورت پیش‌فرض فقط آدرس loopback را می‌پذیرد. استفاده از مقصد
غیرمحلی به گزینه صریح `--allow-remote` نیاز دارد.

نمونه داخل سرور:

```bash
python tools/bale_protocol_e2e.py \
  --messenger-user-id "<TEST_BALE_ID>" \
  --mobile "<TEST_MOBILE>" \
  --personnel-code "<TEST_PERSONNEL_CODE>"
```

توکن بات و secret وب‌هوک نباید در Git یا خروجی گزارش ثبت شوند.

## تست رابط کاربری

در PowerShell:

```powershell
.\backend\tools\start_bale_test_chrome.ps1
```

سپس کاربر فقط یک‌بار در پروفایل جداگانه Chrome وارد حساب آزمایشی بله می‌شود.
رمز و کد یک‌بارمصرف نباید در اختیار عامل هوش مصنوعی قرار گیرد.

MCP موردنیاز Codex:

```powershell
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --browser-url=http://127.0.0.1:9222
```

پس از بازنشانی نشست Codex، عامل می‌تواند صفحه Bale Web را ببیند و دکمه‌ها،
پیام‌ها و جریان‌های رابط کاربری را با حساب آزمایشی بررسی کند.

## مرز امنیتی

- فقط از پروفایل Chrome و حساب بله مخصوص تست استفاده شود.
- remote debugging فقط روی `127.0.0.1` فعال باشد.
- پروفایل اصلی Chrome به MCP متصل نشود.
- پس از پایان تست، Chrome آزمایشی بسته شود.
