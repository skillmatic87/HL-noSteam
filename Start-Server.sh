#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
server_dir="${1:-$project_dir/CS15Server-Linux}"
if (( $# > 0 )); then shift; fi
if [[ ! -f "$server_dir/Start-CS15.sh" || ! -f "$server_dir/hlds" ]]; then
    echo 'Installed server not found. Run bash Setup-Linux.sh first, or use bash Start-Server.sh /path/to/server.' >&2
    exit 1
fi
if [[ -e "$server_dir/.install-incomplete" ]]; then
    echo 'The server installation is incomplete. Complete setup before starting it.' >&2
    exit 1
fi
exec bash "$server_dir/Start-CS15.sh" "$@"
