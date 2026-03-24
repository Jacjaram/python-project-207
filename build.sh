#!/usr/bin/env bash
# Instala uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Instala dependencias del proyecto con Poetry
poetry install --no-root

# Instala Gunicorn en el entorno uv
uv run pip install gunicorn

# Sincroniza uv
uv sync