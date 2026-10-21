"""SOP/OCAP documents for the SOP screen, read from the mounted sop-ocap folder."""

from pathlib import Path

from fastapi import HTTPException
from v1_models import Output

PREFIXES = ("SOP-", "OCAP-")


class SopSummary(Output):
    id: str
    title: str
    category: str
    version: str
    updatedAt: str
    owner: str
    description: str
    tags: list[str]
    demo: bool


class Sop(SopSummary):
    markdown: str


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _parse(path: Path) -> Sop:
    """`# <ID> <제목>`, then the `| 담당 팀 | 버전 | 최근 개정 |` header table."""
    markdown = path.read_text(encoding="utf-8")
    lines = markdown.splitlines()
    doc_id, _, title = lines[0].removeprefix("# ").strip().partition(" ")
    meta: dict[str, str] = {}
    for index, line in enumerate(lines[:-2]):
        if line.startswith("|") and "버전" in _cells(line):
            meta = dict(zip(_cells(line), _cells(lines[index + 2]), strict=False))
            break
    description = next(
        (line.strip() for line in lines[1:] if line.strip() and not line.startswith(("#", "|", ">"))),
        "",
    )
    category = doc_id.split("-")[0]
    return Sop(
        id=doc_id, title=title, category=category, version=meta.get("버전", ""),
        updatedAt=meta.get("최근 개정", ""), owner=meta.get("담당 팀", ""),
        description=description, tags=[category], demo=True, markdown=markdown,
    )


def documents(directory: str) -> list[Sop]:
    """SOPs first, then OCAPs, each by ID. README and research notes are excluded."""
    paths = (path for path in Path(directory).glob("*.md") if path.name.startswith(PREFIXES))
    return sorted((_parse(path) for path in paths), key=lambda doc: (doc.category != "SOP", doc.id))


def summaries(directory: str) -> list[SopSummary]:
    return [SopSummary.model_validate(doc.model_dump(exclude={"markdown"})) for doc in documents(directory)]


def document(directory: str, doc_id: str) -> Sop:
    for doc in documents(directory):
        if doc.id == doc_id:
            return doc
    raise HTTPException(404, "문서를 찾을 수 없습니다.")
