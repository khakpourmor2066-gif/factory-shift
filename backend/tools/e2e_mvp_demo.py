from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable

import uvicorn

backend_root = Path(__file__).resolve().parents[1]
os.environ.setdefault("BALE_SEND_URL", "http://127.0.0.1:9003/send")
os.environ.setdefault("BOT_WEBHOOK_SECRET", "local-dev-secret")

import sys

sys.path.append(str(backend_root))

from tools.webhook_simulator import post_webhook


class ReceiverHandler(BaseHTTPRequestHandler):
    received_messages: list[dict] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        self.received_messages.append({"path": self.path, "body": json.loads(body)})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):
        return


def run_receiver(receiver_port: int) -> HTTPServer:
    ReceiverHandler.received_messages = []
    receiver = HTTPServer(("127.0.0.1", receiver_port), ReceiverHandler)
    threading.Thread(target=receiver.serve_forever, daemon=True).start()
    return receiver


def run_api(api_port: int) -> uvicorn.Server:
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=api_port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


def parse_scenarios(values: Iterable[str]) -> list[tuple[str, str]]:
    scenarios: list[tuple[str, str]] = []
    for value in values:
        if "|" not in value:
            raise ValueError("each scenario must use messenger_user_id|text")
        messenger_user_id, text = value.split("|", 1)
        scenarios.append((messenger_user_id.strip(), text.strip()))
    return scenarios


def render_output(results: list[dict], received_messages: list[dict]) -> str:
    return json.dumps(
        {
            "results": results,
            "received_messages": received_messages,
        },
        ensure_ascii=False,
        indent=2,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local end-to-end MVP demo")
    parser.add_argument("--api-url", default="http://127.0.0.1:8003")
    parser.add_argument("--api-port", type=int, default=8003)
    parser.add_argument("--receiver-port", type=int, default=9003)
    parser.add_argument("--secret", default="local-dev-secret")
    parser.add_argument("--platform", default="bale")
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
    parser.add_argument("--skip-api", action="store_true")
    parser.add_argument("--skip-receiver", action="store_true")
    parser.add_argument("--output", help="Optional path to save the demo result as JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    scenarios = parse_scenarios(args.scenario)

    receiver = run_receiver(args.receiver_port) if not args.skip_receiver else None
    server = run_api(args.api_port) if not args.skip_api else None
    time.sleep(5)

    try:
        results = []
        for messenger_user_id, text in scenarios:
            status_code, body = post_webhook(
                base_url=args.api_url,
                secret=args.secret,
                messenger_user_id=messenger_user_id,
                text=text,
                platform=args.platform,
            )
            results.append(
                {
                    "messenger_user_id": messenger_user_id,
                    "text": text,
                    "status": status_code,
                    "response": json.loads(body),
                }
            )

        output_json = render_output(results, ReceiverHandler.received_messages)
        if args.output:
            Path(args.output).write_text(output_json, encoding="utf-8")
        print(output_json)
        return 0
    finally:
        if server is not None:
            server.should_exit = True
        if receiver is not None:
            receiver.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
