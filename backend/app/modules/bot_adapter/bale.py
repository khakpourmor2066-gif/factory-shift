from __future__ import annotations

import json
from urllib import error, request

from app.core.config import settings
from app.modules.bot_adapter.base import BotAdapter, HttpBotAdapter


class BaleAdapter(BotAdapter):
    def send_message(self, user_id: str, text: str, reply_markup: dict | None = None) -> None:
        if settings.bale_bot_token:
            self._send_via_bale_api(user_id, text, reply_markup)
            return

        if settings.bale_send_url:
            adapter = HttpBotAdapter()
            adapter.send_url = settings.bale_send_url
            adapter.send_message(user_id, text, reply_markup)
            return

        raise RuntimeError("BALE_BOT_TOKEN or BALE_SEND_URL must be configured")

    def _send_via_bale_api(self, user_id: str, text: str, reply_markup: dict | None = None) -> None:
        url = f"{settings.bale_api_base_url.rstrip('/')}/bot{settings.bale_bot_token}/sendMessage"
        message_payload = {"chat_id": user_id, "text": text}
        if reply_markup is not None:
            message_payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        payload = json.dumps(message_payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=10) as response:
                response.read()
        except error.URLError as exc:
            raise RuntimeError(f"failed to send Bale message: {exc}") from exc
