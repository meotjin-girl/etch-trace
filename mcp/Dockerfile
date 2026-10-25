FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY evidence.py business.py rag.py physics.py physics_models.py quantitative_models.py simulation_models.py sensor.py sensor_models.py ingest_sop.py sop_chunks.py sop_vectors.py sop_rerank.py ./

EXPOSE 8000
ENV UV_NO_SYNC=1
CMD ["uv", "run", "python", "business.py"]
