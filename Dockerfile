FROM python:3.11-slim-bookworm

WORKDIR /app

COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY data/corpus ./data/corpus
COPY data/licenses ./data/licenses
COPY data/MANIFEST data/MANIFEST.json ./data/
COPY evals/reports/dashboard.html ./evals/reports/dashboard.html
COPY evals/golden_seed.jsonl ./evals/golden_seed.jsonl

RUN pip install --no-cache-dir -e ".[web]" \
    && mkdir -p data/indexes \
    && AUDIT_RAG_EMBEDDER=hashing AUDIT_RAG_RERANKER=token AUDIT_RAG_GENERATOR=extractive \
       python -m audit_rag ingest --corpus data/corpus --index data/indexes/audit.db

ENV AUDIT_RAG_EMBEDDER=hashing \
    AUDIT_RAG_RERANKER=token \
    AUDIT_RAG_GENERATOR=extractive \
    AUDIT_RAG_INDEX=data/indexes/audit.db \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn audit_rag.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
