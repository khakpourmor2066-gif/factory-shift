from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import error, request

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


def call_bale_api(method: str, payload: dict | None = None) -> tuple[int, str]:
    if not settings.bale_bot_token:
        raise RuntimeError("BALE_BOT_TOKEN is not configured")

    url = f"{settings.bale_api_base_url.rstrip('/')}/bot{settings.bale_bot_token}/{method}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except error.URLError as exc:
        return 0, str(exc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure Bale webhook")
    parser.add_argument("action", choices=["set", "delete", "get"])
    parser.add_argument("--url", default=os.getenv("BALE_WEBHOOK_URL", ""))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.action == "set":
        if not args.url:
            raise RuntimeError("webhook URL is required for set")
        status_code, body = call_bale_api("setWebhook", {"url": args.url})
    elif args.action == "delete":
        status_code, body = call_bale_api("deleteWebhook")
    else:
        status_code, body = call_bale_api("getWebhookInfo")

    print(f"status={status_code}")
    try:
        print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(body)
    return 0 if 200 <= status_code < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
