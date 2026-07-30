from __future__ import annotations

import argparse
import json
import os
from urllib import error, parse, request


def is_loopback_url(base_url: str) -> bool:
    hostname = parse.urlparse(base_url).hostname
    return hostname in {"127.0.0.1", "localhost", "::1"}


def post_bale_message(
    *,
    base_url: str,
    webhook_secret: str,
    messenger_user_id: str,
    text: str,
) -> dict:
    url = f"{base_url.rstrip('/')}/bot/bale/webhook/{webhook_secret}"
    payload = json.dumps(
        {
            "message": {
                "chat": {"id": int(messenger_user_id)},
                "text": text,
            }
        }
    ).encode("utf-8")
    http_request = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"Bale webhook returned HTTP {exc.code}") from exc
    except error.URLError as exc:
        raise RuntimeError("Bale webhook is unavailable") from exc


def run_journey(
    *,
    base_url: str,
    webhook_secret: str,
    messenger_user_id: str,
    mobile: str,
    personnel_code: str,
) -> list[dict]:
    steps = [
        ("phone", mobile, "contact_received"),
        ("code", personnel_code, "access_approved"),
        ("start", "/start", "handled"),
    ]
    results = []
    for name, text, expected_status in steps:
        response = post_bale_message(
            base_url=base_url,
            webhook_secret=webhook_secret,
            messenger_user_id=messenger_user_id,
            text=text,
        )
        status = response.get("status")
        if status != expected_status:
            raise RuntimeError(
                f"{name} returned {status!r}; expected {expected_status!r}"
            )
        results.append(
            {
                "step": name,
                "status": status,
                "message_sent": response.get("message_sent"),
            }
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the two-step Bale activation protocol journey"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--webhook-secret",
        default=os.getenv("BOT_WEBHOOK_SECRET", ""),
    )
    parser.add_argument("--messenger-user-id", required=True)
    parser.add_argument("--mobile", required=True)
    parser.add_argument("--personnel-code", required=True)
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow a non-loopback target that can affect a live user",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.webhook_secret:
        raise RuntimeError("BOT_WEBHOOK_SECRET or --webhook-secret is required")
    if not is_loopback_url(args.base_url) and not args.allow_remote:
        raise RuntimeError("remote targets require --allow-remote")

    results = run_journey(
        base_url=args.base_url,
        webhook_secret=args.webhook_secret,
        messenger_user_id=args.messenger_user_id,
        mobile=args.mobile,
        personnel_code=args.personnel_code,
    )
    print(json.dumps({"ok": True, "steps": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
