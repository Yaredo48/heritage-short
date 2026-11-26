"""Build PROJECT_TECHNICAL_DOCUMENTATION.pdf from TECHNICAL_DOCUMENTATION.md.

    .venv/bin/python docs/technical/build_pdf.py        (or: make techdoc)

Pipeline: Markdown -> HTML (python-markdown) -> PDF (headless Google Chrome,
CSS paged media for headers, footers and page numbers).

Directives understood in the Markdown source (each on its own line):
    @@code path::name        source of a function, class or assignment, cut by `ast`
    @@lines path:START-END   a line range of any file
    @@json path::a.b.0       one value from a JSON file, pretty-printed
    @@fig name [landscape|small] | caption   inline diagrams/<name>.svg as a numbered figure
    Table: caption           numbered table caption (put it just before the table)

Code is read from the repository at build time, so every snippet in the PDF is
the code as it is, with its real file name and line numbers.

Table-of-contents page numbers: pass 1 renders with invisible, absolutely
positioned markers in every heading; pdftotext finds the page of each marker;
pass 2 renders again without markers (they take no space, so the layout is
identical) and with the real page numbers.
"""
from __future__ import annotations

import ast
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = HERE / "TECHNICAL_DOCUMENTATION.md"
CSS = HERE / "style.css"
DIAGRAMS = HERE / "diagrams"
OUT = ROOT / "PROJECT_TECHNICAL_DOCUMENTATION.pdf"


# ---------- directives ----------

def code_block(text: str, lang: str, caption: str) -> str:
    return (f'<figure class="code"><figcaption class="src">{html.escape(caption)}</figcaption>'
            f'<pre><code class="language-{lang}">{html.escape(text)}</code></pre></figure>')


def cut_python(path: Path, name: str) -> tuple[str, int, int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        names = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        if name in names:
            start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
            lines = source.splitlines()[start - 1:node.end_lineno]
            return "\n".join(lines), start, node.end_lineno
    raise SystemExit(f"@@code: {name} not found in {path}")


def expand_directive(line: str, figures: list) -> str | None:
    s = line.strip()
    if s.startswith("@@code "):
        rel, name = s[7:].split("::")
        path = ROOT / rel.strip()
        text, a, b = cut_python(path, name.strip())
        return code_block(text, "python", f"{rel.strip()}, lines {a}–{b}")
    if s.startswith("@@lines "):
        rel, rng = s[8:].rsplit(":", 1)
        a, b = (int(x) for x in rng.split("-"))
        path = ROOT / rel.strip()
        text = "\n".join(path.read_text(encoding="utf-8").splitlines()[a - 1:b])
        lang = {"py": "python", "json": "json", "mk": "make"}.get(path.suffix.lstrip("."), "text")
        if path.name == "Makefile":
            lang = "make"
        return code_block(text, lang, f"{rel.strip()}, lines {a}–{b}")
    if s.startswith("@@json "):
        rel, dotted = s[7:].split("::")
        value = json.loads((ROOT / rel.strip()).read_text(encoding="utf-8"))
        for part in dotted.strip().split("."):
            value = value[int(part)] if part.isdigit() else value[part]
        text = json.dumps(value, indent=2, ensure_ascii=False)
        return code_block(text, "json", f"{rel.strip()} → {dotted.strip()}")
    if s.startswith("@@fig "):
        spec, caption = s[6:].split("|", 1)
        parts = spec.split()
        name, landscape, small = parts[0], "landscape" in parts, "small" in parts
        svg = (DIAGRAMS / f"{name}.svg").read_text(encoding="utf-8")
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
        svg = re.sub(r'style="max-width:[^"]*"', 'style="max-width:100%"', svg, count=1)
        figures.append(name)
        cls = "figure landscape" if landscape else "figure small" if small else "figure"
        return (f'<div class="{cls}"><div class="svgbox">{svg}</div>'
                f'<p class="figcap" data-fig="{name}">{html.escape(caption.strip())}</p></div>')
    return None


def preprocess(md: str, figures: list) -> str:
    out, in_code = [], False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if not in_code:
            expanded = expand_directive(line, figures)
            if expanded is not None:
                out += ["", expanded, ""]
                continue
            # python-markdown needs a blank line before a list that follows a paragraph
            if re.match(r"^\s*(?:[-*]|\d+\.)\s", line) and out and out[-1].strip() \
                    and not re.match(r"^\s*(?:[-*]|\d+\.)\s", out[-1]) and not out[-1].startswith(("    ", "\t")) \
                    and not out[-1].lstrip().startswith(("|", "<")):
                out.append("")
        out.append(line)
    return "\n".join(out)


# ---------- numbering, captions, TOC ----------

def number_and_toc(body: str, with_markers: bool) -> tuple[str, list[dict]]:
    toc, counters = [], [0, 0, 0]

    def heading(m):
        level, attrs, text = int(m.group(1)), m.group(2), m.group(3)
        plain = re.sub("<[^>]+>", "", text)
        counters[level - 1] += 1
        for i in range(level, 3):
            counters[i] = 0
        if level == 1:
            num = f"{counters[0]}"
            label = f'<span class="chapno">Chapter {num}</span>'
        else:
            num = ".".join(str(c) for c in counters[:level])
            label = ""
        hid = f"h-{num.replace('.', '-')}"
        marker = f'<span class="mk">@@M{hid}@@</span>' if with_markers else ""
        toc.append({"level": level, "num": num, "text": plain, "id": hid})
        if level == 1:
            return f'<h1 id="{hid}"{attrs}>{marker}{label}<span class="t">{text}</span></h1>'
        return f'<h{level} id="{hid}"{attrs}>{marker}<span class="n">{num}</span> {text}</h{level}>'

    body = re.sub(r"<h([123])([^>]*)>(.*?)</h\1>", heading, body, flags=re.S)
    body = re.sub(r'<p class="figcap" data-fig="[^"]+">', lambda m: m.group(0) + "§§", body)
    body = re.sub(r"<p>Table: ", '<p class="tabcap">§§', body)
    # number figures and tables in document order, per chapter
    out, pos = [], 0
    pattern = re.compile(r'<h1 id="h-(\d+)"|<p class="(fig)cap"[^>]*>§§|<p class="(tab)cap">§§')
    ch = 0
    nums = {"fig": 0, "tab": 0}
    for m in pattern.finditer(body):
        out.append(body[pos:m.start()])
        if m.group(1):
            ch, nums = int(m.group(1)), {"fig": 0, "tab": 0}
            out.append(m.group(0))
        else:
            kind = "fig" if m.group(2) else "tab"
            nums[kind] += 1
            label = ("Figure" if kind == "fig" else "Table") + f" {ch}.{nums[kind]}."
            out.append(m.group(0).replace("§§", f"<b>{label}</b> "))
        pos = m.end()
    out.append(body[pos:])
    return "".join(out), toc


def toc_html(toc: list[dict], pages: dict[str, int] | None) -> str:
    rows = []
    for t in toc:
        if t["level"] > 2:
            continue
        page = str(pages.get(t["id"], "")) if pages else "000"
        label = f"Chapter {t['num']}&nbsp;&nbsp;{html.escape(t['text'])}" if t["level"] == 1 else \
            f"<span class='n'>{t['num']}</span> {html.escape(t['text'])}"
        rows.append(f'<li class="l{t["level"]}"><a href="#{t["id"]}"><span class="tt">{label}</span>'
                    f'<span class="dots"></span><span class="pg">{page}</span></a></li>')
    return '<nav class="toc"><h2 class="tochead">Contents</h2><ul>' + "".join(rows) + "</ul></nav>"


# ---------- page ----------

def cover(meta: dict) -> str:
    rows = "".join(f"<tr><th>{html.escape(k)}</th><td>{v}</td></tr>" for k, v in meta["control"])
    return f"""
<section class="cover">
  <div class="band"></div>
  <p class="kicker">Technical documentation</p>
  <div class="title">{html.escape(meta["title"])}</div>
  <p class="subtitle">{html.escape(meta['subtitle'])}</p>
  <p class="lede">{meta['lede']}</p>
  <table class="control">{rows}</table>
  <p class="covernote">{meta['note']}</p>
</section>"""


def build_html(with_markers: bool, pages: dict[str, int] | None) -> tuple[str, list[dict]]:
    text = SRC.read_text(encoding="utf-8")
    front, body_md = text.split("\n---\n", 1)
    meta = json.loads(front.strip().removeprefix("<!--").removesuffix("-->"))
    figures: list = []
    body = markdown.markdown(preprocess(body_md, figures),
                             extensions=["tables", "fenced_code", "attr_list", "md_in_html", "sane_lists"])
    body, toc = number_and_toc(body, with_markers)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(meta['title'])} — Technical Documentation</title>
<style>{CSS.read_text(encoding='utf-8')}</style></head>
<body>{cover(meta)}{toc_html(toc, pages)}<main>{body}</main></body></html>"""
    return page, toc


def chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    raise SystemExit("Google Chrome or Chromium is needed to print the PDF")


def print_pdf(page_html: str, out: Path, tmp: Path) -> None:
    src = tmp / "doc.html"
    src.write_text(page_html, encoding="utf-8")
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    "--generate-pdf-document-outline", f"--print-to-pdf={out}", src.as_uri()],
                   check=True, capture_output=True)


def marker_pages(pdf: Path) -> dict[str, int]:
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True,
                                                       text=True, check=True).stdout).group(1))
    found = {}
    for p in range(1, n + 1):
        text = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), str(pdf), "-"],
                              capture_output=True, text=True, check=True).stdout
        for hid in re.findall(r"@@M(h-[\d-]+)@@", text):
            found.setdefault(hid, p)
    return found


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        first, toc = build_html(with_markers=True, pages=None)
        print_pdf(first, tmp / "pass1.pdf", tmp)
        pages = marker_pages(tmp / "pass1.pdf")
        missing = [x["id"] for x in toc if x["level"] <= 2 and x["id"] not in pages]
        if missing:
            print(f"warning: no page found for {missing}")
        final, _ = build_html(with_markers=False, pages=pages)
        (HERE / "build").mkdir(exist_ok=True)
        (HERE / "build" / "TECHNICAL_DOCUMENTATION.html").write_text(final, encoding="utf-8")
        print_pdf(final, OUT, tmp)
    info = subprocess.run(["pdfinfo", str(OUT)], capture_output=True, text=True).stdout
    print(f"{OUT.relative_to(ROOT)}: {re.search(r'Pages:\s+(\d+)', info).group(1)} pages, "
          f"{OUT.stat().st_size // 1024} KB, {len([x for x in toc if x['level'] == 1])} chapters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
