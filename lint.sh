#!/bin/sh

set -o errexit
set -o xtrace

LINT_FILES="r10k"

uv run ruff format $LINT_FILES
uv run ruff check --fix --output-format=full $LINT_FILES
uv run ty check

