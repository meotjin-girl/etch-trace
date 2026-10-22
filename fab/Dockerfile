FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY sensors.py equipment.py collector.py index.html ./

ENV PYTHONUNBUFFERED=1
CMD ["uv", "run", "--no-sync", "python", "collector.py"]
