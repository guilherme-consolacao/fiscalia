FROM python:3.14-slim AS dependencies
WORKDIR /build
COPY requirements.txt requirements-production.txt ./
RUN python -m venv /opt/fiscalia \
    && /opt/fiscalia/bin/pip install --no-cache-dir -r requirements-production.txt

FROM python:3.14-slim
ENV PATH="/opt/fiscalia/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=dependencies /opt/fiscalia /opt/fiscalia
RUN groupadd --system fiscalia \
    && useradd --system --gid fiscalia --no-create-home fiscalia \
    && install -d -o fiscalia -g fiscalia /app/staticfiles
COPY manage.py ./
COPY config ./config
COPY feeds ./feeds
COPY static ./static
COPY templates ./templates
COPY deploy/start.sh ./deploy/start.sh
USER fiscalia
CMD ["/bin/sh", "/app/deploy/start.sh"]
