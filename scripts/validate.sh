#!/usr/bin/env bash
set -euo pipefail

uv run ruff check .
uv run black --check .
uv run pyright
uv run pytest --cov=internal --cov-report=term-missing
