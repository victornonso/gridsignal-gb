FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/api ./apps/api
COPY pipelines ./pipelines
COPY db ./db
COPY alembic.ini ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home gridsignal
USER gridsignal
EXPOSE 8000
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

