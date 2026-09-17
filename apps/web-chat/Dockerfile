FROM node:22-bookworm-slim AS frontend
ARG APP_VERSION=0.0.0-dev
ENV VITE_APP_VERSION=$APP_VERSION
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/tests/request.test.js frontend/tests/stream.test.js ./tests/
RUN npm test && npm run build

FROM python:3.13-slim-bookworm
ARG APP_VERSION=0.0.0-dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.version=$APP_VERSION org.opencontainers.image.revision=$GIT_SHA
ENV APP_VERSION=$APP_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home appuser
COPY app.py auth.py ./
COPY --from=frontend /build/dist ./frontend/dist
RUN IDENTITY_ENDPOINT=http://localhost/identity IDENTITY_HEADER=build-check python -c "import asyncio; from app import FoundryClient, Settings; client = FoundryClient(Settings('tenant', 'client', 'group', 'https://test.services.ai.azure.com')); asyncio.run(client.close())"
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]