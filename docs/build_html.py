"""architecture.md → architecture.html (공유용). md가 원본, html은 생성물.
usage: python3 docs/build_html.py"""
import html
import re
from pathlib import Path

SRC = Path(__file__).with_name("architecture.md")
OUT = Path(__file__).with_name("architecture.html")


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s.replace("✅", '<span class="st ok">✅</span>').replace("🔜", '<span class="st next">🔜</span>').replace("📐", '<span class="st plan">📐</span>')


def cells(line):
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def convert(md):
    out, toc, lines, i = [], [], md.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```mermaid"):
            j = lines.index("```", i + 1)
            out.append(f'<div class="diagram"><pre class="mermaid">{html.escape(chr(10).join(lines[i + 1:j]), quote=False)}</pre></div>')
            i = j + 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            head, body = cells(rows[0]), [cells(r) for r in rows[2:]]
            out.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        if m := re.match(r"(#{1,3}) (.+)", ln):
            level, text = len(m.group(1)), m.group(2)
            if level == 1:
                out.append(f"<h1>{inline(text)}</h1>")
            else:
                hid = f"s{len(toc)}"
                toc.append((level, hid, text))
                out.append(f'<h{level} id="{hid}">{inline(text)}</h{level}>')
        elif ln.startswith("> "):
            out.append(f"<blockquote>{inline(ln[2:])}</blockquote>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.strip() == "---":
            pass
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out), toc


body, toc = convert(SRC.read_text())
nav = "".join(f'<a class="l{lvl}" href="#{hid}">{html.escape(t)}</a>' for lvl, hid, t in toc)
OUT.write_text(f"""<title>TRACE 아키텍처</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* layout: 왼쪽 고정 목차 + 본문 한 열, 다이어그램·표는 자체 가로 스크롤 */
:root {{
  --bg: #f3f6f7; --surface: #ffffff; --ink: #142026; --muted: #56656d; --line: #d6dfe3;
  --accent: #126d70; --accent-soft: #e0f0f0; --amber: #9a5b00; --amber-soft: #fff1da; --code: #e9eef0;
  --sans: 'IBM Plex Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif; --mono: 'IBM Plex Mono', ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0e1517; --surface: #152024; --ink: #e3ecef; --muted: #93a5ad; --line: #2a3a40;
  --accent: #5cc7c9; --accent-soft: #163536; --amber: #f1b65a; --amber-soft: #372810; --code: #1d2b30; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0e1517; --surface: #152024; --ink: #e3ecef; --muted: #93a5ad; --line: #2a3a40;
  --accent: #5cc7c9; --accent-soft: #163536; --amber: #f1b65a; --amber-soft: #372810; --code: #1d2b30; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.7 var(--sans); }}
.shell {{ display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 40px; max-width: 1240px; margin: 0 auto;
  padding-block: 32px 80px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
nav {{ position: sticky; top: calc(env(safe-area-inset-top, 0px) + 24px); align-self: start; max-height: calc(100vh - 48px); overflow-y: auto;
  display: flex; flex-direction: column; gap: 2px; font-size: 13px; border-left: 1px solid var(--line); }}
nav .eyebrow {{ font: 500 11px var(--mono); letter-spacing: .08em; color: var(--accent); padding: 0 12px 8px; text-transform: uppercase; }}
nav a {{ color: var(--muted); text-decoration: none; padding: 3px 12px; border-left: 2px solid transparent; margin-left: -1px; }}
nav a.l3 {{ padding-left: 24px; font-size: 12px; }}
nav a:hover, nav a:focus-visible {{ color: var(--accent); border-left-color: var(--accent); outline: none; }}
article {{ min-width: 0; }}
h1 {{ font-size: 30px; line-height: 1.25; margin: 0 0 16px; text-wrap: balance; letter-spacing: -.01em; }}
h2 {{ font-size: 21px; margin: 56px 0 14px; padding-top: 14px; border-top: 1px solid var(--line); text-wrap: balance; }}
h3 {{ font-size: 16px; margin: 32px 0 10px; color: var(--accent); }}
p, li {{ max-width: 72ch; }} ul {{ padding-left: 20px; }}
blockquote {{ margin: 0 0 16px; padding: 14px 18px; background: var(--accent-soft); border-radius: 8px; font-weight: 500; max-width: 80ch; }}
code {{ font: 13px var(--mono); background: var(--code); padding: 1px 5px; border-radius: 4px; }}
.table-wrap {{ overflow-x: auto; margin: 12px 0 20px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font: 500 12px var(--mono); color: var(--muted); background: var(--bg); white-space: nowrap; }}
tr:last-child td {{ border-bottom: 0; }}
.diagram {{ overflow-x: auto; margin: 14px 0 22px; padding: 18px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }}
.diagram pre {{ margin: 0; min-width: 640px; }}
.st {{ font-style: normal; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 8px; }}
.legend span {{ font: 12px var(--mono); padding: 3px 10px; border-radius: 99px; background: var(--surface); border: 1px solid var(--line); }}
@media (max-width: 860px) {{ .shell {{ grid-template-columns: 1fr; }} nav {{ display: none; }} }}
</style>
<div class="shell">
  <nav aria-label="목차"><div class="eyebrow">TRACE · Architecture v0.2</div>{nav}</nav>
  <article>
    <div class="legend"><span>✅ 오늘 POC 구현</span><span>🔜 다음 단계</span><span>📐 설계만</span></div>
{body}
  </article>
</div>
""")
print(f"wrote {OUT} ({len(toc)} sections)")
