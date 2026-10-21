FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY evidence.py business.py rag.py sop_chunks.py sop_vectors.py sop_rerank.py ./

EXPOSE 8000
CMD ["uv", "run", "python", "business.py"]
