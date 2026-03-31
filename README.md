# RoadCheck

Единый проект для анализа состояния дороги по фотографии.

В корне лежат две части приложения:

- `frontend/` — интерфейс на React + Vite
- `backend/` — API на FastAPI + PostgreSQL + mock/ML-анализ

## Что умеет проект

- регистрация и вход пользователя
- загрузка фотографии дороги
- оценка состояния покрытия в процентах
- вывод найденных дефектов: ямы, трещины, заплатки и т.д.
- история проверок
- профиль пользователя и смена пароля
- выгрузка PDF/JSON отчётов

## Структура

```text
RoadCheck/
├── backend/
├── frontend/
└── README.md
```

## Быстрый запуск

### 1. Поднять backend локально

Создайте виртуальное окружение в корне проекта:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

Создайте файл настроек:

```powershell
Copy-Item backend/.env.example backend/.env
```

Если PostgreSQL уже установлен локально, создайте базу:

```sql
CREATE USER roadcheck WITH PASSWORD 'roadcheck';
CREATE DATABASE roadcheck OWNER roadcheck;
```

Либо можно поднять только БД через Docker:

```powershell
cd backend
docker compose up -d db
cd ..
```

Примените миграции:

```powershell
cd backend
alembic upgrade head
cd ..
```

Опционально наполните проект тестовыми аккаунтами:

```powershell
cd backend
python scripts/seed.py
cd ..
```

Тестовые пользователи после `seed.py`:

- `user@roadcheck.ru` / `user1234`
- `pro@roadcheck.ru` / `pro1234`
- `admin@roadcheck.ru` / `admin1234`

Запуск API:

```powershell
cd backend
uvicorn app.main:app --reload
```

Backend будет доступен на `http://127.0.0.1:8000`.

### 2. Поднять frontend

Установите зависимости:

```powershell
cd frontend
npm install
```

При необходимости создайте локальный `.env`:

```powershell
Copy-Item .env.example .env
```

Запуск фронтенда:

```powershell
npm run dev
```

Frontend будет доступен на `http://127.0.0.1:5173`.

### Полный запуск через Docker Compose

Из корня проекта:

```powershell
docker compose up --build
```

Будут подняты сразу:

- PostgreSQL
- backend на `http://127.0.0.1:8000`
- frontend на `http://127.0.0.1:5173`

Frontend в Docker ходит в backend через nginx-прокси `/api`, поэтому отдельная ручная настройка CORS не нужна.

## Полезные ссылки

- Swagger API: `http://127.0.0.1:8000/docs`
- Основной интерфейс: `http://127.0.0.1:5173`

## Проверка проекта

Backend тесты:

```powershell
cd backend
pytest
```

Frontend production build:

```powershell
cd frontend
npm run build
```
