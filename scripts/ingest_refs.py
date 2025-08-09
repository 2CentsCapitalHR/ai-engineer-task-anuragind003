from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path so `app` package is importable when running as a script
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.rag_indexer import ingest_references


if __name__ == "__main__":
    ingest_references()
