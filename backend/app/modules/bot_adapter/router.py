from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db
from app.modules.access.dependencies import get_current_user
from app.modules.bot_adapter.handlers.bot_handler import resolve_user_message
from app.modules.bot_adapter.schemas.messages import BotIncomingMessage, BotWebhookPayload, BotWebhookResponse
from app.modules.bot_adapter.services.menu_service import get_menu_for_role
from app.modules.bot_adapter.services.bale_webhook_service import resolve_bale_webhook_message
from app.modules.bot_adapter.services.webhook_service import resolve_webhook_message
from app.modules.users.model import User

router = APIRouter(prefix="/bot", tags=["bot-adapter"])


def verify_webhook_secret(x_bot_secret: str | None = Header(default=None, alias="X-Bot-Secret")) -> None:
    if x_bot_secret != settings.bot_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bot webhook secret")


@router.post("/message")
def bot_message_endpoint(
    payload: BotIncomingMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return resolve_user_message(db, current_user, payload.text)


@router.post("/webhook", response_model=BotWebhookResponse)
def bot_webhook_endpoint(
    payload: BotWebhookPayload,
    _: None = Depends(verify_webhook_secret),
    db: Session = Depends(get_db),
):
    return resolve_webhook_message(db, payload)


@router.post("/bale/webhook/{webhook_secret}")
def bale_webhook_endpoint(
    webhook_secret: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    if webhook_secret != settings.bot_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bale webhook secret")
    return resolve_bale_webhook_message(db, payload)


@router.get("/menu")
def bot_menu_endpoint(current_user: User = Depends(get_current_user)):
    return {"items": get_menu_for_role(current_user.role)}
