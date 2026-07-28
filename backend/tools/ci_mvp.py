from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Factory Shift MVP CI command")
    parser.add_argument("--backend-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--artifact", default="artifacts/e2e_output.json")
    parser.add_argument(
        "--scenario",
        action="append",
        default=[
            "emp-1|منو",
            "emp-1|برنامه شیفت من",
            "sup-1|مشاهده افراد یک روز",
        ],
        help="Repeatable messenger_user_id|text scenario",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    backend_root = Path(args.backend_root).resolve()
    artifact_path = backend_root / args.artifact
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    run_command([sys.executable, "-m", "pytest"], backend_root)
    run_command([sys.executable, "-m", "alembic", "upgrade", "head"], backend_root)
    run_command([sys.executable, "tools/seed_mvp.py"], backend_root)

    demo_command = [
        sys.executable,
        "tools/e2e_mvp_demo.py",
        "--output",
        str(artifact_path),
    ]
    for scenario in args.scenario:
        demo_command.extend(["--scenario", scenario])
    run_command(demo_command, backend_root)

    print(f"artifact={artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
