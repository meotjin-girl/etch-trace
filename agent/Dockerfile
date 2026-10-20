FROM python:3.12-slim

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock /app/agent/
RUN cd /app/agent && uv sync --no-dev
COPY . /app/agent
ENV PATH="/app/agent/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
