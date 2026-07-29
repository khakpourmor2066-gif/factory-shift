from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview and confirm Factory Shift data imports")
    parser.add_argument("file", type=Path)
    parser.add_argument("--type", required=True, choices=["employees", "shifts"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser


def run_import(
    *,
    file_path: Path,
    import_type: str,
    base_url: str,
    user_id: int,
    confirm: bool,
    timeout: float,
) -> dict:
    if not file_path.is_file():
        raise ValueError(f"file not found: {file_path}")
    headers = {"X-User-Id": str(user_id)}
    endpoint = f"{base_url.rstrip('/')}/imports/{import_type}/preview"
    with file_path.open("rb") as file_handle:
        response = httpx.post(
            endpoint,
            headers=headers,
            files={"file": (file_path.name, file_handle)},
            timeout=timeout,
        )
    response.raise_for_status()
    preview = response.json()
    result = {"preview": preview}
    if confirm:
        job_id = preview["job"]["id"]
        confirm_response = httpx.post(
            f"{base_url.rstrip('/')}/imports/{job_id}/confirm",
            headers=headers,
            timeout=timeout,
        )
        confirm_response.raise_for_status()
        result["confirmation"] = confirm_response.json()
    return result


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = run_import(
            file_path=args.file,
            import_type=args.type,
            base_url=args.base_url,
            user_id=args.user_id,
            confirm=args.confirm,
            timeout=args.timeout,
        )
    except (ValueError, httpx.HTTPError) as error:
        print(json.dumps({"status": "error", "detail": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
