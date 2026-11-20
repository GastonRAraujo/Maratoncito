FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MARATONCITO_DATABASE_URL=sqlite:////data/maratoncito.db

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
COPY frontend /app/frontend
RUN mkdir -p /data && chown -R 10001:10001 /data /app

USER 10001:10001
EXPOSE 8000
WORKDIR /app/backend
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn maratoncito.main:app --host 0.0.0.0 --port 8000"]
