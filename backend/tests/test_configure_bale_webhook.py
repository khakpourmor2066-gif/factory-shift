import json

from app.core.config import settings
from tools import configure_bale_webhook


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return b'{"ok":true}'


def test_configure_bale_webhook_set(monkeypatch):
    captured = {}

    monkeypatch.setattr(settings, "bale_bot_token", "token-123", raising=False)
    monkeypatch.setattr(settings, "bale_api_base_url", "https://tapi.bale.ai", raising=False)

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(configure_bale_webhook.request, "urlopen", fake_urlopen)

    status_code, body = configure_bale_webhook.call_bale_api("setWebhook", {"url": "https://example.com"})

    assert status_code == 200
    assert captured["url"] == "https://tapi.bale.ai/bottoken-123/setWebhook"
    assert captured["body"] == {"url": "https://example.com"}
    assert body == '{"ok":true}'
