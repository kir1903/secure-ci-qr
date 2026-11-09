import pytest
import requests
import responses

from app import QR_SERVICE_GENERATE_URL, QR_SERVICE_STATUS_URL, app

TASK_ID = "3f2a9c1e-5b7d-4e8a-9c21-7d4e5f6a8b90"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@responses.activate
def test_generate_qr_gateway_success(client):
    """Gateway передаёт задачу в qr-service и возвращает task_id."""
    responses.add(responses.POST, QR_SERVICE_GENERATE_URL, json={"task_id": TASK_ID}, status=202)

    response = client.post("/api/generate", json={"text": "Hello World"})

    assert response.status_code == 202
    assert response.json == {"task_id": TASK_ID}


@responses.activate
def test_status_qr_gateway_success(client):
    """Gateway проксирует статус задачи."""
    responses.add(
        responses.GET,
        QR_SERVICE_STATUS_URL + TASK_ID,
        json={"status": "SUCCESS", "image_base64": "base64str"},
        status=200,
    )

    response = client.get(f"/api/status/{TASK_ID}")

    assert response.status_code == 200
    assert response.json == {"status": "SUCCESS", "image_base64": "base64str"}


def test_generate_without_text_returns_400(client):
    response = client.post("/api/generate", json={})
    assert response.status_code == 400


def test_generate_without_json_body_returns_400(client):
    response = client.post("/api/generate", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_generate_too_long_text_returns_400(client):
    response = client.post("/api/generate", json={"text": "a" * 1001})
    assert response.status_code == 400


@responses.activate
def test_generate_when_qr_service_down_returns_502_without_details(client):
    """При недоступности сервиса клиент не получает текст внутреннего исключения."""
    responses.add(
        responses.POST,
        QR_SERVICE_GENERATE_URL,
        body=requests.ConnectionError("connection refused to http://qr-service:5001"),
    )

    response = client.post("/api/generate", json={"text": "Hello"})

    assert response.status_code == 502
    assert "qr-service:5001" not in response.get_data(as_text=True)


def test_status_with_invalid_task_id_returns_400(client):
    response = client.get("/api/status/..%2F..%2Fadmin")
    assert response.status_code in (400, 404)
    response = client.get("/api/status/<script>")
    assert response.status_code == 400
