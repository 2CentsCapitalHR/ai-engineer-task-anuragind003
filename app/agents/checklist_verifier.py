from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

from app.models.schemas import ChecklistResult, ChecklistItem
from app.core.config import get_settings
from app.services.chains import lc_generate_checklist
from app.services.retriever import FaissRetriever
from app.core.embeddings import embed_texts


def _load_checklist_config() -> Dict[str, List[Dict]]:
    settings = get_settings()
    base_dir = os.path.dirname(os.path.dirname(__file__))  # app/
    config_path = os.path.join(base_dir, "models", "checklists.json")
    if not os.path.exists(config_path):
        # Fallback minimal defaults
        return {
            "Company Incorporation": [
                {"name": "Articles of Association"},
                {"name": "Memorandum of Association"},
                {"name": "Board Resolution"},
                {"name": "UBO Declaration Form"},
                {"name": "Register of Members and Directors"},
            ],
            "Licensing": [
                {"name": "Incorporation Application Form"},
                {"name": "Board Resolution"},
                {"name": "Compliance Policy"},
            ],
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_checklist(process: str, uploaded_doc_types: List[str]) -> Tuple[ChecklistResult, List[ChecklistItem]]:
    # Try dynamic generation via RAG+LLM; fall back to config
    required_items = []
    try:
        retriever = FaissRetriever(top_k=6)
        ctx_hits = []
        for q in [process, "ADGM checklist requirements", "incorporation documents"]:
            ctx_hits.extend(retriever.search(q))
        context = "\n\n".join({h["chunk"] for h in ctx_hits[:6]})
        gen = lc_generate_checklist(process, context)
        if gen:
            required_items = gen
    except Exception:
        required_items = []
    if not required_items:
        cfg = _load_checklist_config()
        required_items = cfg.get(process, [])
    required_names = [it.get("name") for it in required_items if it.get("name")]
    # Semantic match uploaded types to required names (cosine similarity)
    names = [n for n in required_names if n]
    utypes = uploaded_doc_types or []
    present_flags: Dict[str, bool] = {n: False for n in names}
    if names and utypes:
        try:
            name_emb = embed_texts(names)
            type_emb = embed_texts(utypes)
            import numpy as np
            for i, n in enumerate(names):
                sims = (name_emb[i].reshape(1, -1) @ type_emb.T).flatten()
                present_flags[n] = bool(len(sims) and float(np.max(sims)) >= 0.45)
        except Exception:
            # Fallback to exact match if embeddings fail
            uploaded_set = set(utypes)
            for n in names:
                present_flags[n] = n in uploaded_set

    missing = [n for n in names if not present_flags.get(n, False)]

    checklist_items: List[ChecklistItem] = []
    for it in required_items:
        name = it.get("name", "")
        checklist_items.append(
            ChecklistItem(
                name=name,
                rationale=it.get("rationale"),
                source_url=it.get("source_url"),
                present=present_flags.get(name, False),
            )
        )

    return (
        ChecklistResult(
            process=process,
            documents_uploaded=len(uploaded_doc_types),
            required_documents=len(required_names),
            missing_documents=missing,
        ),
        checklist_items,
    )
