"""Section-level source records for the standalone SOP retrieval experiment."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict

ROOT: Final = Path(__file__).resolve().parents[1]
HEADING: Final = re.compile(r"^(#{2,3}) (\d+(?:\.\d+)*)\.? (.+)$", re.MULTILINE)


class Chunk(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: str
    document_id: str
    document_title: str
    section_title: str
    text: str
    source: str
    revision: str
    notice: str
    is_demo: bool = True

    @property
    def embedding_text(self) -> str:
        return f"{self.document_title}\n{self.section_title}\n{self.text}"

    @property
    def content_hash(self) -> str:
        content = f"{self.embedding_text}\n{self.model_dump_json()}"
        return hashlib.sha256(content.encode()).hexdigest()


def parse_document(path: Path) -> list[Chunk]:
    """Keep numbered sections, including parent introductions, without table splitting."""
    source = path.read_text(encoding="utf-8")
    document_title = source.splitlines()[0].removeprefix("# ")
    document_id = document_title.split()[0]
    revision_match = re.search(r"^\| 개정 \| (.+?) \|$", source, re.MULTILINE)
    if revision_match is None:
        raise RuntimeError(f"Missing revision: {path}")
    notice = "\n".join(line[2:] for line in source.splitlines() if line.startswith("> "))
    headings = list(HEADING.finditer(source))
    chunks: list[Chunk] = []
    parent_title = ""
    for index, heading in enumerate(headings):
        level, section, title = heading.groups()
        if level == "##":
            parent_title = title
        if title == "개정 이력":
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        text = source[heading.end() : end].strip()
        if not text:
            continue
        section_title = f"{section} {title}"
        if level == "###":
            section_title = f"{parent_title} / {section_title}"
        chunks.append(
            Chunk(
                id=f"{document_id}#{section}",
                document_id=document_id,
                document_title=document_title,
                section_title=section_title,
                text=text,
                source=f"sop/{path.name}",
                revision=revision_match[1],
                notice=notice,
            )
        )
    return chunks


def load_chunks(directory: Path) -> list[Chunk]:
    """Only SOP/WI/SPEC files are evidence, not README or research notes."""
    paths = sorted(
        path for path in directory.glob("*.md") if path.name.startswith(("SOP-", "WI-", "SPEC-"))
    )
    chunks = [chunk for path in paths for chunk in parse_document(path)]
    if not chunks:
        raise RuntimeError(f"No SOP sections found: {directory}")
    ids = [chunk.id for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate SOP section IDs")
    return chunks
