# RoadCheck Frontend

Интерфейс RoadCheck на React + Vite.

## Подготовка

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

## Запуск

```powershell
npm run dev
```

Приложение откроется на `http://127.0.0.1:5173`.

По умолчанию фронтенд обращается к backend на `http://127.0.0.1:8000`.

## Production build

```powershell
npm run build
```

## Запуск в Docker

Из корня проекта:

```powershell
docker compose up --build
```

Frontend будет доступен на `http://127.0.0.1:5173`.
