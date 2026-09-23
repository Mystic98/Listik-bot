---
status: accepted
---

# Единое приложение FastAPI и React Mini App

Polling aiogram, FastAPI HTTP API, WebSocket и раздача собранного React/Vite/TypeScript frontend работают в одном deployable unit. PostgreSQL остаётся отдельным контейнером. Такое размещение сохраняет простой rollback и единую точку доступа к сервисному слою, пока проект использует один VPS и один экземпляр приложения.

## Consequences

- frontend собирается отдельным multi-stage шагом и поставляется вместе с Python-приложением;
- WebSocket connection manager может быть локальным для одного экземпляра;
- при масштабировании потребуется внешний broker или отдельный realtime-сервис;
- API не должен дублировать бизнес-правила Telegram handlers.
