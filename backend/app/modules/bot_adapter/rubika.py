from app.core.config import settings
from app.modules.bot_adapter.base import HttpBotAdapter


class RubikaAdapter(HttpBotAdapter):
    send_url = settings.rubika_send_url
