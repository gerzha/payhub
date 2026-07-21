FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src/ ./src/

RUN uv pip install --system --no-cache .

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/
COPY alembic.ini ./

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
