#!/usr/bin/env bash
# Instala uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Instala dependencias del proyecto usando Poetry
poetry install --no-root

# Sincroniza uv
uv sync