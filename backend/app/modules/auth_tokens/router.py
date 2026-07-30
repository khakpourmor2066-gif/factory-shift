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
def establish_web_session(
    raw_ticket: str,
    next_path: str = Query(default="/admin/dashboard", alias="next"),
    db: Session = Depends(get_db),
):
    if next_path not in ALLOWED_WEB_REDIRECTS:
        next_path = "/admin/dashboard"
    try:
        _, _, raw_session_token = consume_web_login_ticket(db, raw_ticket)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    response = RedirectResponse(url=next_path, status_code=303)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
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
