from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.modules.auth_tokens.service import create_api_token
from app.modules.users.model import User


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a one-time API token for an existing user")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--name", default="server-bootstrap")
    parser.add_argument("--expires-days", type=int, default=30)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == args.user_id, User.is_active.is_(True)).first()
        if user is None:
            print(json.dumps({"status": "error", "detail": "active user not found"}))
            return 1
        expires_at = datetime.now(UTC) + timedelta(days=args.expires_days)
        token, raw_token = create_api_token(
            db,
            user_id=user.id,
            name=args.name,
            expires_at=expires_at,
        )
        print(
            json.dumps(
                {
                    "status": "created",
                    "token_id": token.id,
                    "user_id": user.id,
                    "expires_at": expires_at.isoformat(),
                    "token": raw_token,
                    "warning": "Store this token now; it cannot be retrieved again.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except ValueError as error:
        print(json.dumps({"status": "error", "detail": str(error)}))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
