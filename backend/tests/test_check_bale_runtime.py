import json

import pytest

from tools import check_bale_runtime


def test_check_bale_runtime_reports_safe_summary(monkeypatch):
    responses = {
        "getMe": (200, json.dumps({"ok": True, "result": {"id": 123, "username": "bot"}})),
        "getWebhookInfo": (
            200,
            json.dumps(
                {
                    "ok": True,
                    "result": {
                        "url": "https://example.com/bot/bale/webhook/private-secret",
                        "pending_update_count": 2,
                    },
                }
            ),
        ),
    }
    monkeypatch.setattr(
        check_bale_runtime,
        "call_bale_api",
        lambda method: responses[method],
    )

    result = check_bale_runtime.check_bale_runtime()

    assert result == {
        "ok": True,
        "bot_api": True,
        "webhook_configured": True,
        "pending_update_count": 2,
        "last_error_present": False,
    }
    assert "private-secret" not in json.dumps(result)


def test_check_bale_runtime_rejects_missing_webhook(monkeypatch):
    responses = {
        "getMe": (200, '{"ok":true,"result":{"id":123}}'),
        "getWebhookInfo": (200, '{"ok":true,"result":{"url":""}}'),
    }
    monkeypatch.setattr(
        check_bale_runtime,
        "call_bale_api",
        lambda method: responses[method],
    )

    with pytest.raises(RuntimeError, match="webhook is not configured"):
        check_bale_runtime.check_bale_runtime()


@pytest.mark.parametrize(
    ("status_code", "body", "message"),
    [
        (503, "unavailable", "HTTP 503"),
        (200, "not-json", "invalid JSON"),
        (200, '{"ok":false}', "unsuccessful"),
    ],
)
def test_parse_success_response_rejects_invalid_provider_response(status_code, body, message):
    with pytest.raises(RuntimeError, match=message):
        check_bale_runtime.parse_success_response("getMe", status_code, body)
