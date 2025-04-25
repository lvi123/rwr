uv pip compile pyproject.toml -o requirements.txt
uv sync
uv venv
source .venv/bin/activate

