"""Export OpenAPI schema to JSON file."""

import json
from pathlib import Path

from mtg_core.api.server import app


def export_openapi_schema(output_path: Path | None = None) -> None:
    """Export the OpenAPI schema to a JSON file."""
    if output_path is None:
        output_path = Path(__file__).parent / "schema" / "openapi.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    schema = app.openapi()
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"OpenAPI schema exported to {output_path}")


if __name__ == "__main__":
    export_openapi_schema()
