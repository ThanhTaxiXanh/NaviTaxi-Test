#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$repo_root/pipeline/vietnam_sovereignty_validator.py" --repo-root "$repo_root" --mode release
