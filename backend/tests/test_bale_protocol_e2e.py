import pytest

from tools import bale_protocol_e2e


def test_loopback_url_detection():
    assert bale_protocol_e2e.is_loopback_url("http://127.0.0.1:8000") is True
    assert bale_protocol_e2e.is_loopback_url("http://localhost:8000") is True
    assert bale_protocol_e2e.is_loopback_url("https://example.com") is False


def test_parser_reads_webhook_secret_from_environment(monkeypatch):
    monkeypatch.setenv("BOT_WEBHOOK_SECRET", "environment-secret")

    args = bale_protocol_e2e.build_parser().parse_args(
        [
            "--messenger-user-id",
            "156546362",
            "--mobile",
            "09120000002",
            "--personnel-code",
            "EMP-001",
        ]
    )

    assert args.webhook_secret == "environment-secret"


def test_protocol_journey_checks_all_expected_statuses(monkeypatch):
    responses = iter(
        [
            {"status": "contact_received", "message_sent": True},
            {"status": "access_approved", "message_sent": True},
            {"status": "handled", "message_sent": True},
        ]
    )
    calls = []

    def fake_post(**kwargs):
        calls.append(kwargs["text"])
        return next(responses)

    monkeypatch.setattr(bale_protocol_e2e, "post_bale_message", fake_post)

    results = bale_protocol_e2e.run_journey(
        base_url="http://127.0.0.1:8000",
        webhook_secret="secret",
        messenger_user_id="156546362",
        mobile="09120000002",
        personnel_code="EMP-001",
    )

    assert calls == ["09120000002", "EMP-001", "/start"]
    assert [item["status"] for item in results] == [
        "contact_received",
        "access_approved",
        "handled",
    ]


def test_protocol_journey_stops_on_unexpected_status(monkeypatch):
    monkeypatch.setattr(
        bale_protocol_e2e,
        "post_bale_message",
        lambda **kwargs: {"status": "identity_missing"},
    )

    with pytest.raises(RuntimeError, match="expected 'contact_received'"):
        bale_protocol_e2e.run_journey(
            base_url="http://127.0.0.1:8000",
            webhook_secret="secret",
            messenger_user_id="156546362",
            mobile="09120000002",
            personnel_code="EMP-001",
        )
