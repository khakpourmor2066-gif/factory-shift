from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.seed.mvp_seed import seed_mvp_data
from tools.seed_access_demo import ensure_demo_access_requests


SCENARIOS = {"mvp", "access_demo", "all"}


def seed_scenario(db, scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")

    result: dict = {"scenario": scenario}
    if scenario in {"mvp", "all"}:
        result["mvp"] = seed_mvp_data(db)
    if scenario in {"access_demo", "all"}:
        result["access_requests_created"] = ensure_demo_access_requests(db)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed stable MVP scenarios.")
    parser.add_argument(
        "scenario",
        nargs="?",
        default="all",
        choices=sorted(SCENARIOS),
        help="Seed scenario to run.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = seed_scenario(db, args.scenario)
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
