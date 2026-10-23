FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY langgraph.json ./
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    LANGSMITH_TRACING=false
EXPOSE 2024
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser", "--no-reload"]
