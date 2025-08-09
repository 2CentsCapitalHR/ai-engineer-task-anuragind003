from __future__ import annotations

import os
from typing import List
import json
import os
from docx import Document

from app.models.schemas import IntakeDoc, IntakeResult
from app.core.llm import get_llm_client
from app.services.chains import lc_classify_doc


DOC_TYPE_KEYWORDS = {
    "Articles of Association": ["articles of association", "aoa"],
    "Memorandum of Association": ["memorandum of association", "moa", "mou"],
    "Board Resolution": ["board resolution"],
    "Shareholder Resolution": ["shareholder resolution"],
    "Incorporation Application Form": ["incorporation application"],
    "UBO Declaration Form": ["ubo", "ultimate beneficial owner"],
    "Register of Members and Directors": ["register of members", "register of directors"],
    "Change of Registered Address Notice": ["change of registered address", "registered address"],
}


def _read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _classify(text: str) -> str:
    # LLM-zero-shot classification constrained to known labels (primary)
    try:
        labels = _load_labels()
        if labels:
            label, _ = lc_classify_doc(text, labels)
            if label and label in labels:
                return label
    except Exception:
        pass
    # Fallback: keyword heuristic (offline)
    lower = text.lower()
    for label, tokens in DOC_TYPE_KEYWORDS.items():
        if any(tok in lower for tok in tokens):
            return label
    return "Unknown"


def _load_labels() -> List[str]:
    base_dir = os.path.dirname(os.path.dirname(__file__))  # app/
    cfg = os.path.join(base_dir, "models", "doc_types.json")
    try:
        with open(cfg, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [it.get("label") for it in data if it.get("label")]
    except Exception:
        return list(DOC_TYPE_KEYWORDS.keys())


def run_doc_intake(file_paths: List[str]) -> IntakeResult:
    docs: List[IntakeDoc] = []
    for path in file_paths:
        if not os.path.exists(path):
            continue
        if os.path.splitext(path)[1].lower() != ".docx":
            continue
        text = _read_docx(path)
        doc_type = _classify(text)
        docs.append(IntakeDoc(filename=os.path.basename(path), doc_type=doc_type, text=text))
    return IntakeResult(docs=docs)
