from __future__ import annotations

import os
import json
from typing import List, Dict
import faiss
import numpy as np

from app.core.config import get_settings
from app.core.embeddings import embed_texts


class FaissRetriever:
    def __init__(self, top_k: int = 5):
        self.settings = get_settings()
        index_path = os.path.join(self.settings.faiss_index_dir, "index.faiss")
        chunks_path = os.path.join(self.settings.faiss_index_dir, "chunks.json")
        meta_path = os.path.join(self.settings.faiss_index_dir, "meta.json")
        if not (os.path.exists(index_path) and os.path.exists(chunks_path)):
            raise RuntimeError("FAISS index not found. Run scripts/ingest_refs.py first.")
        self.index = faiss.read_index(index_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks: List[str] = json.load(f)
        with open(meta_path, "r", encoding="utf-8") as f:
            self.meta: List[Dict] = json.load(f)
        self.top_k = top_k

    def search(self, query: str) -> List[Dict]:
        q_vec = embed_texts([query])
        scores, idxs = self.index.search(q_vec, self.top_k)
        results: List[Dict] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            chunk = self.chunks[idx]
            meta = self.meta[idx]
            results.append({
                "score": float(score),
                "chunk": chunk,
                "ref_id": f"{os.path.basename(meta['source_path'])}#chunk-{meta['chunk_index']}",
                "source_path": meta.get("source_path", ""),
                "title": meta.get("title", os.path.basename(meta.get("source_path", ""))),
                "source_url": meta.get("source_url", None),
            })
        return results
