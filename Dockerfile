FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ["server/requirements.txt", "server/requirements.txt"]
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r "server/requirements.txt"

COPY server server
COPY ml_engine ml_engine

ENV SDP_TEMP_REPO_DIR=/tmp/sdp_github_temp_repos
ENV PREDICTION_HISTORY_DB_PATH=/var/data/prediction_history.db
ENV ALLOW_LOCAL_CACHE_MODE=false
ENV MAX_SOURCE_FILES_PER_RUN=500

WORKDIR /app/server

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]