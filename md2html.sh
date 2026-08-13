#!/usr/bin/env sh
# Convert Markdown to HTML. Usage: ./md2html.sh [input.md] [-o output.html] [--title T]
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPT="$SCRIPT_DIR/md2html.py"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT" "$@"
else
    echo "ERROR: Python 3 not found. Please install Python 3.8+." >&2
    exit 1
fi
