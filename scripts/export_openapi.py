"""Validate and optionally export the FastAPI OpenAPI schema."""

import argparse
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "backend"))

from maratoncito.main import app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate the generated OpenAPI document")
    parser.add_argument("--output", type=Path, help="Write the OpenAPI document")
    args = parser.parse_args()
    spec = app.openapi()
    assert "/health" in spec["paths"]
    assert "/api/v1/system/status" in spec["paths"]
    assert spec["info"]["title"] == "Maratoncito API"
    if args.output:
        args.output.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    elif not args.check:
        print(json.dumps(spec, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
