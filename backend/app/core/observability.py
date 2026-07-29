import json
import logging
import threading
import time
import uuid
from collections import Counter

from fastapi import Request


logger = logging.getLogger("factory_shift.requests")
_counter_lock = threading.Lock()
_request_counts: Counter[tuple[str, str, int]] = Counter()
_request_duration_seconds = 0.0


async def request_observability_middleware(request: Request, call_next):
    global _request_duration_seconds

    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    started_at = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        duration = time.perf_counter() - started_at
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        with _counter_lock:
            _request_counts[(request.method, path, status_code)] += 1
            _request_duration_seconds += duration
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
                ensure_ascii=False,
            )
        )


def render_metrics() -> str:
    with _counter_lock:
        counts = dict(_request_counts)
        total_duration = _request_duration_seconds
    lines = [
        "# HELP factory_shift_http_requests_total Total HTTP requests.",
        "# TYPE factory_shift_http_requests_total counter",
    ]
    for (method, path, status_code), count in sorted(counts.items()):
        lines.append(
            "factory_shift_http_requests_total"
            f'{{method="{method}",path="{path}",status="{status_code}"}} {count}'
        )
    lines.extend(
        [
            "# HELP factory_shift_http_request_duration_seconds_sum Total request duration.",
            "# TYPE factory_shift_http_request_duration_seconds_sum counter",
            f"factory_shift_http_request_duration_seconds_sum {total_duration:.6f}",
        ]
    )
    return "\n".join(lines) + "\n"
