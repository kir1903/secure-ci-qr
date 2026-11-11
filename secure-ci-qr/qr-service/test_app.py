import base64

import pytest

from app import app, create_qr_task


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_qr_service_endpoint_success(client, mocker):
    """POST /generate ставит задачу в очередь и возвращает task_id."""
    mock_task = mocker.Mock()
    mock_task.id = "mock_task_id"
    mocker.patch("app.create_qr_task.delay", return_value=mock_task)

    response = client.post("/generate", json={"text": "Mocked Flow"})

    assert response.status_code == 202
    assert response.json == {"task_id": "mock_task_id"}


def test_generate_without_text_returns_400(client):
    response = client.post("/generate", json={})
    assert response.status_code == 400


def test_generate_too_long_text_returns_400(client):
    response = client.post("/generate", json={"text": "a" * 1001})
    assert response.status_code == 400


def test_generate_hides_internal_error(client, mocker):
    """Если брокер недоступен, клиент не видит текст исключения."""
    mocker.patch("app.create_qr_task.delay", side_effect=ConnectionError("redis://secret-host:6379"))

    response = client.post("/generate", json={"text": "Hello"})

    assert response.status_code == 500
    assert "secret-host" not in response.get_data(as_text=True)


def test_qr_task_returns_png(mocker):
    """Сама задача генерирует корректный PNG (без задержки)."""
    mocker.patch("app.time.sleep")

    result = create_qr_task.run("https://urfu.ru")

    assert base64.b64decode(result).startswith(b"\x89PNG")
