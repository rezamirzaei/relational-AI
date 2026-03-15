#!/usr/bin/env python3
"""Export the OpenAPI schema from the FastAPI application.

Usage:
    python scripts/export_openapi.py

Writes the schema to docs/openapi.json. CI uses this to detect schema
drift between the committed file and the current codebase.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure deterministic settings so the export is reproducible in CI.
os.environ.setdefault("RFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("RFI_JWT_SECRET", "openapi-export-only-key-not-for-runtime-0001")
os.environ.setdefault("RFI_APP_ENV", "local")

# Add src to the path so the package is importable without pip install.
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from relational_fraud_intelligence.app import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    schema = app.openapi()

    output_path = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"OpenAPI schema written to {output_path} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
