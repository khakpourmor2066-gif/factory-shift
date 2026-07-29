from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.configure_bale_webhook import call_bale_api


def parse_success_response(method: str, status_code: int, body: str) -> dict:
    if status_code != 200:
        raise RuntimeError(f"{method} returned HTTP {status_code}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} returned invalid JSON") from exc
    if payload.get("ok") is not True:
        raise RuntimeError(f"{method} returned an unsuccessful response")
    return payload


def check_bale_runtime() -> dict:
    get_me_status, get_me_body = call_bale_api("getMe")
    get_me = parse_success_response("getMe", get_me_status, get_me_body)

    webhook_status, webhook_body = call_bale_api("getWebhookInfo")
    webhook = parse_success_response("getWebhookInfo", webhook_status, webhook_body)
    webhook_result = webhook.get("result") or {}
    webhook_url = str(webhook_result.get("url") or "").strip()
    if not webhook_url:
        raise RuntimeError("Bale webhook is not configured")

    return {
        "ok": True,
        "bot_api": bool(get_me.get("result")),
        "webhook_configured": True,
        "pending_update_count": int(webhook_result.get("pending_update_count") or 0),
        "last_error_present": bool(webhook_result.get("last_error_message")),
    }


def main() -> int:
    try:
        result = check_bale_runtime()
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
