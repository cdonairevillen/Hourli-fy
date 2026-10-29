"""Escribe el contrato de la API en specs/api/openapi.yaml a partir de la app FastAPI.

Uso: cd backend && uv run python scripts/export_openapi.py
"""

import sys
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

OUTPUT = BACKEND_DIR.parent / "specs" / "api" / "openapi.yaml"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"Contrato escrito en {OUTPUT}")


if __name__ == "__main__":
    main()
