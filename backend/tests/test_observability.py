from fastapi.testclient import TestClient

from app.main import app


def test_liveness_and_metrics_include_request_id():
    client = TestClient(app)

    live = client.get("/health/live", headers={"X-Request-Id": "test-request-id"})
    metrics = client.get("/metrics")

    assert live.status_code == 200
    assert live.headers["X-Request-Id"] == "test-request-id"
    assert metrics.status_code == 200
    assert "factory_shift_http_requests_total" in metrics.text
