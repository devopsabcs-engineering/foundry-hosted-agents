FROM python:3.11-slim
ARG APP_VERSION=0.0.0-dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.version=$APP_VERSION org.opencontainers.image.revision=$GIT_SHA
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

ENV PORT=8000
EXPOSE 8000

CMD ["python", "main.py"]
