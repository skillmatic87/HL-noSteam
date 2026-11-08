#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null; then
    echo 'Python 3 is required. Install it with: sudo apt install python3' >&2
    exit 1
fi
exec python3 "$project_dir/scripts/install_cs15_linux.py" "$@"
