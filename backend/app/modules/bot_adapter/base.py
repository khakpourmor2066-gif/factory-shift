from __future__ import annotations

import json
from urllib import error, request


class BotAdapter:
    def send_message(self, user_id: str, text: str, reply_markup: dict | None = None) -> None:
        raise NotImplementedError


class HttpBotAdapter(BotAdapter):
    send_url: str = ""

    def send_message(self, user_id: str, text: str, reply_markup: dict | None = None) -> None:
        if not self.send_url:
            raise RuntimeError("send_url is not configured")

        payload = {"user_id": user_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        http_request = request.Request(
            self.send_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=10) as response:
                response.read()
        except error.URLError as exc:
            raise RuntimeError(f"failed to send bot message: {exc}") from exc
