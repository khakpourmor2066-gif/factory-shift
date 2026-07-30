from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.observability import render_metrics, request_observability_middleware
from app.main import app


def test_liveness_and_metrics_include_request_id():
    client = TestClient(app)

    live = client.get("/health/live", headers={"X-Request-Id": "test-request-id"})
    metrics = client.get("/metrics")

    assert live.status_code == 200
    assert live.headers["X-Request-Id"] == "test-request-id"
    assert metrics.status_code == 200
    assert "factory_shift_http_requests_total" in metrics.text


def test_metrics_use_route_templates_instead_of_sensitive_path_values():
    isolated_app = FastAPI()
    isolated_app.middleware("http")(request_observability_middleware)

    @isolated_app.get("/sensitive/{secret}")
    def sensitive_route(secret: str):
        return {"ok": True}

    client = TestClient(isolated_app)
    sensitive_ticket = "sensitive-one-time-ticket"

    response = client.get(f"/sensitive/{sensitive_ticket}")
    metrics = render_metrics()

    assert response.status_code == 200
    assert sensitive_ticket not in metrics
    assert "/sensitive/{secret}" in metrics
