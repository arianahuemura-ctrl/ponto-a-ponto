#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${PAP_PUBLIC_PYTHON:-$HOME/.virtualenvs/bus/bin/python}" "$ROOT/scripts/public_instance.py" start
