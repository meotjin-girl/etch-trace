"""SOP screen API over a temporary sop-ocap style folder."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import Wire, headers
from fastapi.testclient import TestClient
from main import create_app
from v1_models import Settings

HEADER = "| 담당 팀 | 버전 | 최근 개정 |\n| --- | --- | --- |\n| {owner} | {version} | 2026-10-20 |\n"


@pytest.fixture
def sop_client(database_url: str, wire: Wire, tmp_path: Path) -> Iterator[TestClient]:
    (tmp_path / "OCAP-TEST-RF_RF.md").write_text(
        "# OCAP-TEST-RF RF 반사전력 이상 대응\n\n" + HEADER.format(owner="설비팀", version="1.1")
        + "\n## 1. 적용 범위\n\n| 항목 | 내용 |\n| --- | --- |\n| a | b |\n\n반사전력 상승 대응 절차입니다.\n",
        encoding="utf-8",
    )
    (tmp_path / "SOP-TEST-12_이상대응.md").write_text(
        "# SOP-TEST-12 식각 장비 이상 대응\n\n" + HEADER.format(owner="공정팀", version="1.0")
        + "\n## 1. 목적\n\n공통 조사 흐름을 정합니다.\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# 목록\n", encoding="utf-8")
    (tmp_path / "00_notes.md").write_text("# 메모\n", encoding="utf-8")
    app = create_app(Settings(database_url, wire.url, "test-key", str(tmp_path)))
    with TestClient(app) as client:
        yield client


def test_sop_list_reads_header_table_and_skips_notes(sop_client: TestClient) -> None:
    rows = sop_client.get("/api/sops", headers=headers()).json()
    assert [row["id"] for row in rows] == ["SOP-TEST-12", "OCAP-TEST-RF"]
    assert rows[1] == {
        "id": "OCAP-TEST-RF", "title": "RF 반사전력 이상 대응", "category": "OCAP",
        "version": "1.1", "updatedAt": "2026-10-20", "owner": "설비팀",
        "description": "반사전력 상승 대응 절차입니다.", "tags": ["OCAP"], "demo": True,
    }


def test_sop_detail_returns_markdown_and_errors(sop_client: TestClient) -> None:
    detail = sop_client.get("/api/sops/SOP-TEST-12", headers=headers()).json()
    assert detail["markdown"].startswith("# SOP-TEST-12")
    assert detail["owner"] == "공정팀"
    missing = sop_client.get("/api/sops/NOPE", headers=headers())
    assert missing.status_code == 404
    assert missing.json() == {"detail": "문서를 찾을 수 없습니다."}
    assert sop_client.get("/api/sops").status_code == 401


def test_repository_sop_ocap_documents_all_parse() -> None:
    from v1_models import DEFAULT_SOP_DIR
    from v1_sop import summaries

    rows = summaries(DEFAULT_SOP_DIR)
    assert len(rows) == 22
    assert {row.category for row in rows} == {"SOP", "OCAP"}
    assert all(row.owner and row.version and row.updatedAt and row.description for row in rows)
