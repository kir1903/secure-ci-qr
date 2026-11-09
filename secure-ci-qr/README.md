# QR Generator — Security CI

[![Security CI](https://github.com/kir1903/secure-ci-qr/actions/workflows/security-ci.yml/badge.svg)](https://github.com/kir1903/secure-ci-qr/actions/workflows/security-ci.yml)

Микросервисное веб-приложение для генерации QR-кодов (пример преподавателя из Practice105, DenisovAV), в которое встроен CI-процесс с автоматическими проверками безопасности. Лабораторная работа 108 «Secure CI» по дисциплине «Программная инженерия» (УрФУ).

## Архитектура

```
Браузер → frontend (nginx, :8080) → gateway (Flask) → qr-service (Flask) → Redis ← qr-worker (Celery)
```

| Сервис | Назначение |
|---|---|
| `frontend` | Статический интерфейс и обратный прокси `/api/` (nginx от непривилегированного пользователя) |
| `gateway` | API-шлюз: валидация запроса, проксирование в qr-service |
| `qr-service` | Ставит задачу генерации QR-кода в очередь Celery и отдаёт её статус |
| `qr-worker` | Celery-воркер, генерирует PNG |
| `redis` | Брокер задач и хранилище результатов |

## Запуск

```bash
docker compose up --build
```

Приложение: http://localhost:8080

## Тесты локально

```bash
cd gateway && pip install -r requirements-dev.txt && pytest -v
cd ../qr-service && pip install -r requirements-dev.txt && pytest -v
```

## Security CI

Workflow: [`.github/workflows/security-ci.yml`](.github/workflows/security-ci.yml). Запускается при `push` и `pull request` в `main`, а также вручную.

| Задача | Инструмент | Что проверяет |
|---|---|---|
| Tests | pytest | Автотесты gateway и qr-service (матрица) |
| SAST | Bandit, Semgrep | Уязвимые конструкции в Python-коде и Dockerfile |
| Secrets | Gitleaks | Токены, пароли и ключи во всей истории git |
| Vulnerability scan | Trivy | Уязвимые зависимости, ошибки конфигурации Dockerfile, секреты |
