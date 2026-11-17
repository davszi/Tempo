FROM node:22-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build

# Litestream copies the SQLite database to object storage so it survives restarts (deploy/README.md).
FROM alpine:3.20 AS litestream
ARG LITESTREAM_VERSION=0.5.17
ARG LITESTREAM_SHA256=cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d
RUN wget -qO /tmp/litestream.tar.gz \
        "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-x86_64.tar.gz" \
    && echo "${LITESTREAM_SHA256}  /tmp/litestream.tar.gz" | sha256sum -c - \
    && mkdir /out && tar -xzf /tmp/litestream.tar.gz -C /out && test -x /out/litestream

FROM python:3.13-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt gunicorn==23.0.0
COPY --from=litestream /out/litestream /usr/local/bin/litestream
COPY deploy/litestream.yml /etc/litestream.yml
COPY deploy/start.sh ./deploy/start.sh
COPY backend/*.py backend/fitted_global.csv backend/tempo_demo.sqlite ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV PYTHONDONTWRITEBYTECODE=1
ENV TEMPO_DATABASE=/var/data/tempo.sqlite
CMD ["sh", "deploy/start.sh"]
