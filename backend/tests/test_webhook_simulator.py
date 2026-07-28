from urllib import error

from tools.webhook_simulator import post_webhook


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return b'{"ok":true}'


def test_post_webhook_sends_expected_request(monkeypatch):
    captured = {}

    def fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        captured["secret"] = http_request.headers["X-bot-secret"]
        captured["content_type"] = http_request.headers["Content-type"]
        captured["body"] = http_request.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr("tools.webhook_simulator.request.urlopen", fake_urlopen)

    status_code, body = post_webhook("http://localhost:8000/", "secret", "emp-1", "منو", "bale")

    assert status_code == 200
    assert body == '{"ok":true}'
    assert captured["url"] == "http://localhost:8000/bot/webhook"
    assert captured["timeout"] == 10
    assert captured["secret"] == "secret"
    assert captured["content_type"] == "application/json"
    assert "emp-1" in captured["body"]


def test_post_webhook_handles_connection_error(monkeypatch):
    def fake_urlopen(http_request, timeout):
        raise error.URLError("connection refused")

    monkeypatch.setattr("tools.webhook_simulator.request.urlopen", fake_urlopen)

    status_code, body = post_webhook("http://localhost:8000", "secret", "emp-1", "منو", "bale")

    assert status_code == 0
    assert "connection refused" in body
