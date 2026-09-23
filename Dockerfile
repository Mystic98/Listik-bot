FROM node:22-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY bot.py config.py database.py handlers.py states.py utils.py categories.py models.py ./
COPY database_backend.py docker-entrypoint.sh ./
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY webapp/ ./webapp/
COPY --from=frontend-build /frontend/dist ./frontend/dist

RUN mkdir -p /app/data /app/logs

RUN chmod +x /app/docker-entrypoint.sh

CMD ["/app/docker-entrypoint.sh"]
