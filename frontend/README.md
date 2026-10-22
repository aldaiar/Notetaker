# Notetaker — frontend (React + Vite, JavaScript)

Разработка:
    npm install
    npm run dev          # http://localhost:5173, /api проксируется на http://localhost:8000
    API_URL=http://host:8000 npm run dev   # другой адрес бэкенда

Docker: сервис `web` (см. docker-compose.snippet.yml) — nginx отдаёт сборку и проксирует /api на api:8000.
