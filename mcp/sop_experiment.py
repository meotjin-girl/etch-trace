"""Run with: uv run --project mcp --group rag-experiment python mcp/sop_experiment.py."""

from __future__ import annotations

import hashlib
from pathlib import Path
from time import perf_counter
from typing import Annotated, ClassVar, Final, Literal, assert_never

import psycopg
import typer
from dotenv import dotenv_values
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, TypeAdapter
from sop_chunks import ROOT, load_chunks
from sop_rerank import CANDIDATE_K, DEFAULT_METHOD, RERANK_MODEL, RetrievalMethod, rerank
from sop_vectors import MODEL, Embedder, EmbeddingModel, Hit, ingest, retrieve

DATABASE_URL: Final = "postgresql://trace:trace@localhost:55432/trace_sop"
KEY_FILE: Final = ROOT.parent / "etch_trace_poc" / ".env"
QUESTIONS: Final = ROOT / "mcp" / "sop_questions.json"
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)

DatabaseOption = Annotated[str, typer.Option(envvar="SOP_DATABASE_URL")]
KeyOption = Annotated[Path, typer.Option(exists=True, dir_okay=False)]


class Question(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: str
    category: Literal["direct", "paraphrase", "multi", "out_of_scope"]
    query: str
    expected_ids: list[str]


class ExpectedRank(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: str
    rank: int | None
    distance: float | None


class EvaluationRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    question: Question
    passed: bool | None
    hits: list[Hit]
    dense_expected_ranks: list[ExpectedRank]
    candidate_contains_all_expected: bool | None


class Evaluation(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model: EmbeddingModel
    method: RetrievalMethod
    rerank_model: str | None
    candidate_k: int | None
    top_k: int = 3
    passed: int
    answerable: int
    target: int = 11
    meets_target: bool
    tokens: int
    questions_sha256: str
    embedding_seconds: float
    retrieval_seconds: float
    rerank_seconds: float
    rerank_input_tokens: int
    rerank_output_tokens: int
    results: list[EvaluationRow]


def openai_client(env_file: Path) -> OpenAI:
    """Read only the key; do not import another project's database or model settings."""
    key = dotenv_values(env_file).get("OPENAI_API_KEY")
    if not key:
        raise typer.BadParameter(f"OPENAI_API_KEY is missing in {env_file}")
    return OpenAI(api_key=key, timeout=60.0, max_retries=0)


def score(question: Question, hits: list[Hit]) -> bool | None:
    """All required sections must appear; out-of-scope results are observation only."""
    if not question.expected_ids:
        return None
    return set(question.expected_ids).issubset(hit.id for hit in hits)


@app.command("ingest")
def ingest_command(
    sop_dir: Annotated[Path, typer.Option(exists=True, file_okay=False)] = ROOT / "sop-ocap",
    database_url: DatabaseOption = DATABASE_URL,
    env_file: KeyOption = KEY_FILE,
    model: Annotated[EmbeddingModel, typer.Option()] = MODEL,
) -> None:
    chunks = load_chunks(sop_dir)
    with openai_client(env_file) as client, psycopg.connect(database_url) as connection:
        result = ingest(connection, Embedder(client, model), chunks)
    typer.echo(result.model_dump_json(indent=2))


@app.command("search")
def search_command(
    query: Annotated[str, typer.Argument()],
    top_k: Annotated[int, typer.Option(min=1)] = 3,
    database_url: DatabaseOption = DATABASE_URL,
    env_file: KeyOption = KEY_FILE,
    model: Annotated[EmbeddingModel, typer.Option()] = MODEL,
    method: Annotated[RetrievalMethod, typer.Option()] = DEFAULT_METHOD,
) -> None:
    if not query.strip():
        raise typer.BadParameter("query must contain text")
    if method is RetrievalMethod.RERANK and top_k != 3:
        raise typer.BadParameter("rerank mode returns exactly three sections")
    with openai_client(env_file) as client, psycopg.connect(database_url) as connection:
        vectors, _ = Embedder(client, model).embed([query])
        match method:
            case RetrievalMethod.DENSE:
                hits = retrieve(connection, vectors[0], top_k)
            case RetrievalMethod.RERANK:
                candidates = retrieve(connection, vectors[0], CANDIDATE_K)
                hits = rerank(client, query, candidates).hits
            case _:
                assert_never(method)
    typer.echo(TypeAdapter(list[Hit]).dump_json(hits, indent=2).decode())


@app.command("evaluate")
def evaluate_command(
    database_url: DatabaseOption = DATABASE_URL,
    env_file: KeyOption = KEY_FILE,
    output: Annotated[Path | None, typer.Option(dir_okay=False)] = None,
    model: Annotated[EmbeddingModel, typer.Option()] = MODEL,
    questions_file: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = QUESTIONS,
    minimum_passed: Annotated[int, typer.Option(min=1)] = 11,
    method: Annotated[RetrievalMethod, typer.Option()] = DEFAULT_METHOD,
) -> None:
    question_bytes = questions_file.read_bytes()
    questions = TypeAdapter(list[Question]).validate_json(question_bytes)
    with openai_client(env_file) as client, psycopg.connect(database_url) as connection:
        started = perf_counter()
        vectors, tokens = Embedder(client, model).embed([question.query for question in questions])
        embedding_seconds = perf_counter() - started
        started = perf_counter()
        rows: list[EvaluationRow] = []
        rerank_seconds = 0.0
        rerank_input_tokens = 0
        rerank_output_tokens = 0
        for question, vector in zip(questions, vectors, strict=True):
            candidates = retrieve(connection, vector, None)
            match method:
                case RetrievalMethod.DENSE:
                    hits = candidates[:3]
                case RetrievalMethod.RERANK:
                    ranked = rerank(client, question.query, candidates[:CANDIDATE_K])
                    hits = ranked.hits
                    rerank_seconds += ranked.seconds
                    rerank_input_tokens += ranked.input_tokens
                    rerank_output_tokens += ranked.output_tokens
                case _:
                    assert_never(method)
            ranks = {hit.id: (rank, hit.distance) for rank, hit in enumerate(candidates, 1)}
            expected_ranks = [
                ExpectedRank(
                    id=id,
                    rank=ranks.get(id, (None, None))[0],
                    distance=ranks.get(id, (None, None))[1],
                )
                for id in question.expected_ids
            ]
            rows.append(
                EvaluationRow(
                    question=question,
                    passed=score(question, hits),
                    hits=hits,
                    dense_expected_ranks=expected_ranks,
                    candidate_contains_all_expected=score(question, candidates[:CANDIDATE_K]),
                )
            )
        retrieval_seconds = perf_counter() - started - rerank_seconds
    answerable = sum(row.passed is not None for row in rows)
    passed = sum(row.passed is True for row in rows)
    result = Evaluation(
        model=model,
        method=method,
        rerank_model=RERANK_MODEL if method is RetrievalMethod.RERANK else None,
        candidate_k=CANDIDATE_K if method is RetrievalMethod.RERANK else None,
        passed=passed,
        answerable=answerable,
        target=minimum_passed,
        meets_target=passed >= minimum_passed,
        tokens=tokens,
        questions_sha256=hashlib.sha256(question_bytes).hexdigest(),
        embedding_seconds=embedding_seconds,
        retrieval_seconds=retrieval_seconds,
        rerank_seconds=rerank_seconds,
        rerank_input_tokens=rerank_input_tokens,
        rerank_output_tokens=rerank_output_tokens,
        results=rows,
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        _ = output.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    for row in rows:
        status = "OBSERVE" if row.passed is None else ("PASS" if row.passed else "FAIL")
        ids = ", ".join(f"{hit.id} ({hit.distance:.4f})" for hit in row.hits)
        typer.echo(f"{row.question.id} {status}: {ids}")
        if row.passed is False:
            expected_summary = [(rank.id, rank.rank) for rank in row.dense_expected_ranks]
            typer.echo(f"  dense_expected_ranks={expected_summary}")
    summary = f"model={model}; method={method}; answerable={passed}/{answerable}"
    typer.echo(f"{summary}; target={minimum_passed}/{answerable}; tokens={tokens}")
    if not result.meets_target:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
