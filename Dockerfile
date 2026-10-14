# Imagen de producción de InmoBot. Heroku la construye desde heroku.yml (no hace falta Docker local).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_PATH=/tmp/inmobot/inmobot.db

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY static ./static
COPY properties.json .

# Sin privilegios de root. SQLite vive en /tmp: disco efímero, solo demo con datos de prueba.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
# Heroku asigna el puerto en $PORT; local usa 8000.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
