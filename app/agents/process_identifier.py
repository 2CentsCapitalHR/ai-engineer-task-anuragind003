from __future__ import annotations

from typing import List
from app.services.chains import lc_detect_process


def detect_process(doc_types: List[str]) -> str:
    # LLM-based process detection first
    try:
        text = " ".join(doc_types)
        proc, conf, _ = lc_detect_process(doc_types, text)
        return proc or "Unknown"
    except Exception:
        pass
    # Fallback heuristic
    lowered = [d.lower() for d in doc_types]
    if any("articles of association" in d for d in lowered) or any("memorandum of association" in d for d in lowered):
        return "Company Incorporation"
    if any("licence" in d or "license" in d for d in lowered):
        return "Licensing"
    return "Unknown"


def detect_process_from_texts(texts: List[str]) -> str:
    """Heuristic detection using raw document texts, for offline fallback.

    Looks for key phrases indicative of Incorporation vs Licensing.
    """
    haystack = "\n".join(texts or []).lower()
    if not haystack:
        return "Unknown"

    incorporation_tokens = [
        "articles of association",
        "memorandum of association",
        "application for incorporation",
        "incorporation application",
        "subscriber",
        "share capital",
    ]
    licensing_tokens = [
        "licence",
        "license",
        "commercial licence",
        "business license",
        "operating licence",
    ]

    if any(tok in haystack for tok in incorporation_tokens):
        return "Company Incorporation"
    if any(tok in haystack for tok in licensing_tokens):
        return "Licensing"
    return "Unknown"