"""knowledge/*.md → '## ' 단위 chunk → OpenAI embedding → doc_chunks. 문서가 바뀔 때만 실행."""
import json
from pathlib import Path

import db
from tools import EMBED_MODEL, embed


def chunks(path):
    for part in path.read_text().split("\n## ")[1:]:
        title, _, body = part.partition("\n")
        yield path.name, title.strip(), f"{title.strip()}\n{body.strip()}"


if __name__ == "__main__":
    db.init()
    items = [c for p in sorted(Path(__file__).with_name("knowledge").glob("*.md")) for c in chunks(p)]
    vecs = embed([c[2] for c in items])
    db.q("TRUNCATE doc_chunks")
    for (src, sec, text), v in zip(items, vecs):
        db.q("INSERT INTO doc_chunks (source, section, content, embedding, embed_model) VALUES (%s,%s,%s,%s::vector,%s)",
             (src, sec, text, json.dumps(v), EMBED_MODEL))
    print(f"indexed {len(items)} chunks with {EMBED_MODEL}")
