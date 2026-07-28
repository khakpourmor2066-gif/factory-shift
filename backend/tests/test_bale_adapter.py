import json

from app.core.config import settings
from app.modules.bot_adapter import bale as bale_module
from app.modules.bot_adapter.bale import BaleAdapter


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return b'{"ok":true}'


def test_bale_adapter_uses_official_api_when_token_exists(monkeypatch):
    captured = {}

    monkeypatch.setattr(settings, "bale_bot_token", "token-123", raising=False)
    monkeypatch.setattr(settings, "bale_api_base_url", "https://tapi.bale.ai", raising=False)
    monkeypatch.setattr(settings, "bale_send_url", "", raising=False)

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        captured["headers"] = http_request.headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(bale_module.request, "urlopen", fake_urlopen)

    BaleAdapter().send_message("12345", "سلام")

    assert captured["url"] == "https://tapi.bale.ai/bottoken-123/sendMessage"
    assert captured["body"] == {"chat_id": "12345", "text": "سلام"}
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["timeout"] == 10


def test_bale_adapter_falls_back_to_local_send_url(monkeypatch):
    captured = {}

    monkeypatch.setattr(settings, "bale_bot_token", "", raising=False)
    monkeypatch.setattr(settings, "bale_send_url", "http://127.0.0.1:9003/send", raising=False)

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(bale_module.request, "urlopen", fake_urlopen)

    BaleAdapter().send_message("emp-1", "منو")

    assert captured["url"] == "http://127.0.0.1:9003/send"
    assert captured["body"] == {"user_id": "emp-1", "text": "منو"}
