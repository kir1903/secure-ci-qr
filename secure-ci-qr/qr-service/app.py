import base64
import io
import logging
import os
import time

import qrcode
from celery import Celery
from flask import Flask, jsonify, request

app = Flask(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
MAX_TEXT_LENGTH = 1000

app.config.update(CELERY_BROKER_URL=REDIS_URL, CELERY_RESULT_BACKEND=REDIS_URL)

celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"], backend=app.config["CELERY_RESULT_BACKEND"])

logger = logging.getLogger(__name__)


@celery.task
def create_qr_task(text: str):
    """Асинхронно генерирует QR-код и возвращает PNG в base64."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    time.sleep(5)  # имитация долгой обработки

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    return base64.b64encode(img_buffer.getvalue()).decode("utf-8")


@app.route("/generate", methods=["POST"])
def generate_qr_async():
    data = request.get_json(silent=True) or {}
    text = data.get("text")

    if not text or not isinstance(text, str):
        return jsonify({"error": "No text provided"}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({"error": f"Text is longer than {MAX_TEXT_LENGTH} characters"}), 400

    try:
        task = create_qr_task.delay(text)
    except Exception:
        # Подробности пишем в лог, а клиенту не раскрываем внутреннюю ошибку
        logger.exception("Failed to enqueue QR task")
        return jsonify({"error": "Failed to create task"}), 500

    return jsonify({"task_id": task.id}), 202


@app.route("/status/<task_id>", methods=["GET"])
def get_status(task_id):
    task = create_qr_task.AsyncResult(task_id)
    if task.state == "PENDING":
        return jsonify({"status": "PENDING"}), 200
    if task.state != "FAILURE":
        return jsonify({"status": "SUCCESS", "image_base64": task.info}), 200

    logger.error("QR task %s failed: %s", task_id, task.info)
    return jsonify({"status": "FAILURE", "error": "QR generation failed"}), 500


if __name__ == "__main__":
    # Локальный запуск для разработки. В контейнере сервис запускается через gunicorn (см. Dockerfile).
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "127.0.0.1"),
        port=5001,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
