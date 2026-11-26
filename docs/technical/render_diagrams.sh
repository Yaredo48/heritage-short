#!/usr/bin/env bash
# Render diagrams/*.mmd to SVG (embedded in the PDF) and PNG (standalone copies).
# Needs Node and mermaid-cli. Uses the system Chrome instead of downloading one:
#   PUPPETEER_SKIP_DOWNLOAD=1 npm i -g @mermaid-js/mermaid-cli@11.12.0
#   MMDC=mmdc CHROME=/usr/bin/google-chrome ./render_diagrams.sh
set -euo pipefail
cd "$(dirname "$0")/diagrams"
MMDC="${MMDC:-mmdc}"
CHROME="${CHROME:-/usr/bin/google-chrome}"
PPTR="$(mktemp)"
printf '{"executablePath":"%s","args":["--no-sandbox"]}' "$CHROME" > "$PPTR"
for src in *.mmd; do
  name="${src%.mmd}"
  "$MMDC" -q -p "$PPTR" -c mermaid.config.json -b white --svgId "fig-$name" -i "$src" -o "$name.svg"
  "$MMDC" -q -p "$PPTR" -c mermaid.config.json -b white -s 2 -i "$src" -o "$name.png"
  echo "rendered $name"
done
rm -f "$PPTR"
