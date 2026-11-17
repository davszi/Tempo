FROM node:22-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build

FROM python:3.13-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt gunicorn==23.0.0
COPY backend/*.py backend/fitted_global.csv backend/tempo_demo.sqlite ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV PYTHONDONTWRITEBYTECODE=1
ENV TEMPO_DATABASE=/var/data/tempo.sqlite
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 'backend.hosting:hosted_app()'"]
