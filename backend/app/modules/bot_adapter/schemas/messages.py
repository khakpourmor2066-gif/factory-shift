from pydantic import BaseModel


class BotIncomingMessage(BaseModel):
    messenger_user_id: str
    text: str
    platform: str = "bale"


class BotWebhookPayload(BaseModel):
    messenger_user_id: str
    text: str
    platform: str | None = None


class BotWebhookResponse(BaseModel):
    ok: bool
    platform: str
    messenger_user_id: str
    response: dict
