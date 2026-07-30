from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user
from app.modules.auth_tokens.schema import ApiTokenCreate, ApiTokenCreated, ApiTokenRead
from app.modules.auth_tokens.service import (
    WEB_SESSION_COOKIE,
    WEB_SESSION_HOURS,
    consume_web_login_ticket,
    create_api_token,
    inspect_web_login_ticket,
    list_api_tokens,
    revoke_api_token,
    revoke_web_session,
)
from app.modules.users.model import User


router = APIRouter(prefix="/auth/tokens", tags=["authentication"])
session_router = APIRouter(prefix="/admin/session", tags=["web-session"])
ALLOWED_WEB_REDIRECTS = {
    "/admin/dashboard",
    "/admin/imports",
    "/admin/schedule-generator",
}


@router.post("", response_model=ApiTokenCreated)
def create_token_endpoint(
    token_in: ApiTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        token, raw_token = create_api_token(
            db,
            user_id=current_user.id,
            name=token_in.name,
            expires_at=token_in.expires_at,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    token_data = ApiTokenRead.model_validate(token, from_attributes=True)
    return ApiTokenCreated(
        **token_data.model_dump(),
        token=raw_token,
    )


@router.get("", response_model=list[ApiTokenRead])
def list_tokens_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_api_tokens(db, current_user.id)


@router.delete("/{token_id}", response_model=ApiTokenRead)
def revoke_token_endpoint(
    token_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return revoke_api_token(db, current_user.id, token_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@session_router.get("/{raw_ticket}", include_in_schema=False)
def show_web_session_confirmation(
    raw_ticket: str,
    next_path: str = Query(default="/admin/dashboard", alias="next"),
    db: Session = Depends(get_db),
):
    next_path = _allowed_next_path(next_path)
    try:
        inspect_web_login_ticket(db, raw_ticket)
    except ValueError as error:
        return _invalid_login_link_response(str(error))

    return HTMLResponse(
        content=f"""
        <html lang="fa" dir="rtl">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>ورود امن به پیشخوان</title>
            <style>
              body {{ font-family: sans-serif; background: #f6f7f9; margin: 0; padding: 24px; }}
              main {{ max-width: 520px; margin: 10vh auto; background: white; border: 1px solid #ddd;
                      border-radius: 14px; padding: 24px; line-height: 1.9; }}
              button {{ width: 100%; padding: 12px; font: inherit; cursor: pointer; color: white;
                        background: #087f5b; border: 0; border-radius: 9px; }}
              .hint {{ color: #555; }}
            </style>
          </head>
          <body>
            <main>
              <h1>ورود امن به پیشخوان</h1>
              <p>لینک معتبر است. برای ایجاد نشست مدیریتی، دکمه زیر را بزنید.</p>
              <p class="hint">این تأیید از مصرف لینک توسط پیش‌نمایش پیام‌رسان جلوگیری می‌کند.</p>
              <form method="post" action="/admin/session/{raw_ticket}/confirm?next={next_path}">
                <button type="submit">ورود به پیشخوان مدیریت</button>
              </form>
            </main>
          </body>
        </html>
        """,
        status_code=200,
        headers=_web_login_headers(),
    )


@session_router.post("/{raw_ticket}/confirm", include_in_schema=False)
def establish_web_session(
    raw_ticket: str,
    next_path: str = Query(default="/admin/dashboard", alias="next"),
    db: Session = Depends(get_db),
):
    next_path = _allowed_next_path(next_path)
    try:
        _, _, raw_session_token = consume_web_login_ticket(db, raw_ticket)
    except ValueError as error:
        return _invalid_login_link_response(str(error))

    response = RedirectResponse(url=next_path, status_code=303)
    response.headers.update(_web_login_headers())
    response.set_cookie(
        key=WEB_SESSION_COOKIE,
        value=raw_session_token,
        max_age=WEB_SESSION_HOURS * 60 * 60,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return response


def _allowed_next_path(next_path: str) -> str:
    return next_path if next_path in ALLOWED_WEB_REDIRECTS else "/admin/dashboard"


def _web_login_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": (
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'"
        ),
    }


def _invalid_login_link_response(reason: str) -> HTMLResponse:
    message = (
        "مهلت این لینک پایان یافته است."
        if reason == "expired web login link"
        else "این لینک قبلاً استفاده شده یا دیگر معتبر نیست."
    )
    return HTMLResponse(
        content=f"""
        <html lang="fa" dir="rtl">
          <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
          <title>لینک ورود نامعتبر</title></head>
          <body style="font-family:sans-serif;background:#f6f7f9;padding:24px;line-height:1.9">
            <main style="max-width:520px;margin:10vh auto;background:white;border:1px solid #ddd;
                         border-radius:14px;padding:24px">
              <h1>ورود انجام نشد</h1>
              <p>{message}</p>
              <p>به ربات بله بازگردید و از بخش راهنما یک لینک ورود تازه بسازید.</p>
            </main>
          </body>
        </html>
        """,
        status_code=401,
        headers=_web_login_headers(),
    )


@session_router.post("/logout", include_in_schema=False)
def close_web_session(
    web_session: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    if web_session:
        revoke_web_session(db, web_session)
    response = HTMLResponse(
        content=(
            '<html lang="fa" dir="rtl"><meta charset="utf-8">'
            "<title>خروج از پیشخوان</title>"
            "<p>با موفقیت از پیشخوان وب خارج شدید.</p></html>"
        ),
        status_code=200,
        headers={"Cache-Control": "no-store"},
    )
    response.delete_cookie(
        key=WEB_SESSION_COOKIE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return response
