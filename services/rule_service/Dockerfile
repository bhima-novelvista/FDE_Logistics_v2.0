# =====================================================================
# Rule service image (v2.0 Step 4).
#
# Build and start it with docker compose from the project folder:
#   docker compose -f services/rule_service/docker-compose.yml --env-file .env up -d --build --wait
#
# - Small official Python image; exact package versions (requirements.txt).
# - Runs as an ordinary user, not as root.
# - Listens on port 8101 inside the container; docker compose publishes it
#   on 127.0.0.1 only, so it cannot be reached from your network.
# - No secrets are baked into the image: settings come from docker compose
#   at start-up.
# =====================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the packages first, so a code change does not reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8101

# The factory reads the settings and the rules file first and refuses to
# start if the rules file has mistakes. Our own middleware logs each request.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8101", "--no-access-log"]
