# RoadCheck Backend

FastAPI backend для анализа дорожного покрытия.

## Стек

- Python 3.10+
- FastAPI
- SQLAlchemy 2 Async
- Alembic
- PostgreSQL
- YOLO/mock-анализ

## Подготовка

Из корня проекта:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

## Запуск БД

Вариант 1: локальный PostgreSQL.

```sql
CREATE USER roadcheck WITH PASSWORD 'roadcheck';
CREATE DATABASE roadcheck OWNER roadcheck;
```

Вариант 2: Docker.

```powershell
cd backend
docker compose up -d db
```

## Миграции

```powershell
cd backend
alembic upgrade head
```

## Наполнение тестовыми данными

```powershell
python scripts/seed.py
```

Демо-аккаунты:

- `user@roadcheck.ru` / `user1234`
- `pro@roadcheck.ru` / `pro1234`
- `admin@roadcheck.ru` / `admin1234`

## Запуск API

```powershell
cd backend
uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`

Swagger: `http://127.0.0.1:8000/docs`

## Реальный YOLO-режим

По умолчанию backend использует `USE_MOCK_ML=true`.

Чтобы переключиться на настоящую модель:

1. Положите веса в `backend/app/ml/weights/best.pt` или задайте путь через `ML_MODEL_PATH`.
2. В `backend/.env` установите `USE_MOCK_ML=false`.
3. Перезапустите API. На старте backend попробует загрузить модель сразу и завершится с ошибкой, если веса отсутствуют или не читаются.

Текущий режим можно проверить через `GET /health`.

## Запуск в Docker

Из корня проекта:

```powershell
docker compose up --build
```

## Тесты

```powershell
cd backend
pytest
```
