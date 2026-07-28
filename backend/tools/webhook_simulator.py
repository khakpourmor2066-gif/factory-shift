from __future__ import annotations

import argparse
import json
from urllib import error, request


def post_webhook(base_url: str, secret: str, messenger_user_id: str, text: str, platform: str) -> tuple[int, str]:
    payload = json.dumps(
        {
            "messenger_user_id": messenger_user_id,
            "text": text,
            "platform": platform,
        }
    ).encode("utf-8")
    http_request = request.Request(
        f"{base_url.rstrip('/')}/bot/webhook",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Bot-Secret": secret,
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except error.URLError as exc:
        return 0, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local bot webhook simulator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--secret", default="local-dev-secret")
    parser.add_argument("--messenger-user-id", default="emp-1")
    parser.add_argument("--text", default="منو")
    parser.add_argument("--platform", default="bale")
    args = parser.parse_args()

    status_code, body = post_webhook(
        base_url=args.base_url,
        secret=args.secret,
        messenger_user_id=args.messenger_user_id,
        text=args.text,
        platform=args.platform,
    )
    print(f"status={status_code}")
    try:
        print(json.dumps(json.loads(body), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(body)
    return 0 if 200 <= status_code < 300 else 1


if __name__ == "__main__":
    raise SystemExit(main())
