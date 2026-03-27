FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY bot.py config.py database.py handlers.py states.py utils.py categories.py models.py ./

RUN mkdir -p /app/data /app/logs

RUN useradd --create-home botuser
RUN chown -R botuser:botuser /app
USER botuser

CMD ["uv", "run", "python", "bot.py"]
