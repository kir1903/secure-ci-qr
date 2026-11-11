import logging
import os
import uuid

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)

# CORS разрешён только для явно заданных источников (по умолчанию — для фронтенда на localhost:8080)
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
CORS(app, origins=ALLOWED_ORIGINS)

logger = logging.getLogger(__name__)

QR_SERVICE_URL = os.environ.get("QR_SERVICE_URL", "http://qr-service:5001")
QR_SERVICE_GENERATE_URL = f"{QR_SERVICE_URL}/generate"
QR_SERVICE_STATUS_URL = f"{QR_SERVICE_URL}/status/"

# Таймаут запросов к внутреннему сервису (секунды): без него gateway может зависнуть навсегда
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))
MAX_TEXT_LENGTH = 1000


def _normalize_task_id(task_id: str):
    """task_id — это UUID задачи Celery. Возвращает нормализованный UUID или None."""
    try:
        return str(uuid.UUID(task_id))
    except ValueError:
        return None


@app.route("/api/generate", methods=["POST"])
def generate_qr():
    data = request.get_json(silent=True) or {}
    text = data.get("text")

    if not text or not isinstance(text, str):
        return jsonify({"error": "No text provided"}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({"error": f"Text is longer than {MAX_TEXT_LENGTH} characters"}), 400

    try:
        response = requests.post(QR_SERVICE_GENERATE_URL, json={"text": text}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("QR service request failed")
        return jsonify({"error": "QR service is unavailable"}), 502

    return jsonify({"task_id": response.json().get("task_id")}), 202


@app.route("/api/status/<task_id>", methods=["GET"])
def check_status(task_id):
    safe_task_id = _normalize_task_id(task_id)
    if safe_task_id is None:
        return jsonify({"error": "Invalid task id"}), 400

    # Защита от SSRF: адрес внутреннего сервиса фиксирован в конфигурации, а в путь
    # подставляется только проверенный и нормализованный UUID, поэтому запрос
    # не может уйти на другой хост или другой путь.
    status_url = f"{QR_SERVICE_STATUS_URL}{safe_task_id}"
    try:
        response = requests.get(status_url, timeout=REQUEST_TIMEOUT)  # nosemgrep: python.flask.security.injection.ssrf-requests
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("QR service request failed")
        return jsonify({"error": "QR service is unavailable"}), 502

    return jsonify(response.json()), 200


if __name__ == "__main__":
    # Локальный запуск для разработки. В контейнере сервис запускается через gunicorn (см. Dockerfile).
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
