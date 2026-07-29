from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import error, request

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.modules.users.model import User
from tools.seed_scenarios import seed_scenario


def http_get_json(url: str, headers: dict[str, str] | None = None) -> tuple[int, str]:
    http_request = request.Request(url, headers=headers or {}, method="GET")
    try:
        with request.urlopen(http_request, timeout=15) as response:
            return response.status, response.read().decode("utf-8")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except error.URLError as exc:
        return 0, str(exc)


def http_post_json(url: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    http_request = request.Request(url, data=body, headers=merged_headers, method="POST")
    try:
        with request.urlopen(http_request, timeout=15) as response:
            return response.status, response.read().decode("utf-8")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")
    except error.URLError as exc:
        return 0, str(exc)


def find_supervisor_user_id() -> int:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.role == "SUPERVISOR")
            .filter(User.is_active.is_(True))
            .order_by(User.id.asc())
            .first()
        )
        if user is None:
            raise RuntimeError("active supervisor user not found")
        return user.id
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Production smoke test for Factory Shift")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--seed", default="all", choices=["mvp", "access_demo", "all"])
    parser.add_argument("--run-seed", action="store_true", help="Seed demo data before checks")
    parser.add_argument("--dashboard-path", default="/admin/dashboard")
    parser.add_argument("--health-path", default="/health")
    parser.add_argument("--readiness-path", default="/health/ready")
    parser.add_argument("--bot-path", default="/bot/webhook")
    parser.add_argument("--bot-user-id", default="emp-1")
    parser.add_argument("--bot-text", default="منو")
    parser.add_argument("--bot-secret", default="local-dev-secret")
    parser.add_argument("--api-token", default="")
    parser.add_argument("--skip-dashboard", action="store_true")
    parser.add_argument("--skip-bot", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.run_seed:
        db = SessionLocal()
        try:
            seed_result = seed_scenario(db, args.seed)
        finally:
            db.close()
        print(json.dumps({"seed": seed_result}, ensure_ascii=False))

    health_status, health_body = http_get_json(f"{args.base_url.rstrip('/')}{args.health_path}")
    if health_status != 200:
        print(f"health_status={health_status}")
        print(health_body)
        return 1

    readiness_status, readiness_body = http_get_json(
        f"{args.base_url.rstrip('/')}{args.readiness_path}"
    )
    if readiness_status != 200:
        print(f"readiness_status={readiness_status}")
        print(readiness_body)
        return 1

    supervisor_user_id = find_supervisor_user_id()
    api_headers = (
        {"Authorization": f"Bearer {args.api_token}"}
        if args.api_token
        else {"X-User-Id": str(supervisor_user_id)}
    )

    dashboard_status = 200
    dashboard_body = ""
    if not args.skip_dashboard:
        dashboard_status, dashboard_body = http_get_json(
            f"{args.base_url.rstrip('/')}{args.dashboard_path}",
            headers=api_headers,
        )
        if dashboard_status != 200:
            print(f"dashboard_status={dashboard_status}")
            print(dashboard_body)
            return 1

    bot_status = 200
    bot_body = ""
    if not args.skip_bot:
        bot_status, bot_body = http_post_json(
            f"{args.base_url.rstrip('/')}{args.bot_path}",
            {
                "messenger_user_id": args.bot_user_id,
                "text": args.bot_text,
                "platform": "bale",
            },
            headers={"X-Bot-Secret": args.bot_secret},
        )
        if bot_status != 200:
            print(f"bot_status={bot_status}")
            print(bot_body)
            return 1

    print(
        json.dumps(
            {
                "health": {"status": health_status, "body": json.loads(health_body)},
                "readiness": {
                    "status": readiness_status,
                    "body": json.loads(readiness_body),
                },
                "dashboard": {"status": dashboard_status, "user_id": supervisor_user_id},
                "bot": {"status": bot_status, "messenger_user_id": args.bot_user_id},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
