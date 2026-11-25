"""Export docs/REPORT.md to docs/REPORT.pdf and docs/REPORT.docx (for the submission form).

Markdown -> HTML (python-markdown) -> PDF and DOCX (LibreOffice, headless).
Usage: make report
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "REPORT.md"

CSS = """
body { font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 10.5pt; line-height: 1.4; }
h1 { font-size: 18pt; margin-bottom: 4pt; }
h2 { font-size: 13pt; margin-top: 14pt; border-bottom: 1px solid #999; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
th, td { border: 1px solid #999; padding: 3pt 5pt; vertical-align: top; font-size: 9.5pt; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 9pt; }
blockquote { color: #555; border-left: 3px solid #bbb; margin-left: 0; padding-left: 8pt; }
"""


def main() -> int:
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        print("LibreOffice not found; install it, or print the HTML to PDF from a browser.")
        return 1
    text = SRC.read_text(encoding="utf-8")
    if "✍️" in text:
        print("warning: REPORT.md still has ✍️ placeholders; fill them before submitting.")
    # python-markdown needs a blank line before a list that follows a paragraph line (GitHub does not).
    text = re.sub(r"(?m)^(?![ \t]*(?:[-*]|\d+\.) )(.+)\n(?=[ \t]*(?:[-*]|\d+\.) )", r"\1\n\n", text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    body = body.replace("<table>", '<table border="1" cellpadding="4" cellspacing="0" width="100%">')
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "REPORT.html"
        page.write_text(html, encoding="utf-8")
        for target in ("pdf:writer_web_pdf_Export", "docx:MS Word 2007 XML"):
            subprocess.run([office, "--headless", "--convert-to", target, "--outdir", str(DOCS), str(page)],
                           check=True, capture_output=True)
    for ext in ("pdf", "docx"):
        out = DOCS / f"REPORT.{ext}"
        print(f"{out.relative_to(DOCS.parent)}: {out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
