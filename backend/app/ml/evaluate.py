"""Print the persisted model's reproducible held-out evaluation summary."""
from __future__ import annotations

import json

from app.ml.model import MODEL_PATH, metadata


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit("No model artifact found. Run: python -m app.ml.train")
    print(json.dumps(metadata(), indent=2))


if __name__ == "__main__":
    main()
