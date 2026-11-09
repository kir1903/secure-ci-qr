import logging
import os

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


def _validate_task_id(task_id: str) -> bool:
    """task_id — это UUID Celery: только hex-символы и дефисы."""
    return 0 < len(task_id) <= 64 and all(c in "0123456789abcdef-" for c in task_id.lower())


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
    except requests.RequestException:
        logger.exception("QR service is unavailable")
        return jsonify({"error": "QR service is unavailable"}), 502

    if response.status_code != 202:
        return jsonify({"error": "QR task failed"}), 502

    return jsonify(response.json()), 202


@app.route("/api/status/<task_id>", methods=["GET"])
def check_status(task_id):
    if not _validate_task_id(task_id):
        return jsonify({"error": "Invalid task id"}), 400

    try:
        response = requests.get(f"{QR_SERVICE_STATUS_URL}{task_id}", timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        logger.exception("QR service is unavailable")
        return jsonify({"error": "QR service is unavailable"}), 502

    return jsonify(response.json()), response.status_code


if __name__ == "__main__":
    # Локальный запуск для разработки. В контейнере сервис запускается через gunicorn (см. Dockerfile).
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
