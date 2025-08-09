from __future__ import annotations

from typing import Any, Dict, List, Tuple
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableLambda

from app.core.llm import get_llm_client


def _run_text(prompt_tmpl: str, **kwargs: Any) -> str:
    llm = get_llm_client()
    if llm is None:
        raise RuntimeError("LLM not configured")
    prompt = PromptTemplate.from_template(prompt_tmpl).format(**kwargs)
    # Use a minimal LCEL chain to comply with 'use langchain'
    chain = RunnableLambda(lambda p: llm.generate_text(p))
    return chain.invoke(prompt)


def _run_json_list(prompt_tmpl: str, **kwargs: Any) -> List[Dict[str, Any]]:
    llm = get_llm_client()
    if llm is None:
        raise RuntimeError("LLM not configured")
    prompt = PromptTemplate.from_template(prompt_tmpl).format(**kwargs)
    chain = RunnableLambda(lambda p: llm.generate_json_list(p))
    return chain.invoke(prompt)


def lc_classify_doc(text: str, labels: List[str]) -> Tuple[str, float]:
    tmpl = (
        "Classify the document into one label from this list: {labels}.\n"
        "Return strict JSON: {{label: <string from labels>, confidence: <0..1>}}.\n\n"
        "Document (truncated):\n{text}"
    )
    try:
        out = _run_json_list(tmpl, labels=labels, text=text[:1800])
        if isinstance(out, dict):
            data = out
        elif out and isinstance(out[0], dict):
            data = out[0]
        else:
            return "Unknown", 0.0
        label = data.get("label", "Unknown")
        conf = float(data.get("confidence", 0.0) or 0.0)
        return label, conf
    except Exception:
        return "Unknown", 0.0


def lc_detect_process(doc_types: List[str], text: str) -> Tuple[str, float, List[str]]:
    tmpl = (
        "You detect the legal process attempted (e.g., 'Company Incorporation', 'Licensing').\n"
        "Given doc types {doc_types} and content, return strict JSON: {process: <string>, confidence: <0..1>, alternatives: [<strings>]}.\n\n"
        "Content (truncated):\n{text}"
    )
    try:
        out = _run_json_list(tmpl, doc_types=doc_types, text=text[:2400])
        data = out if isinstance(out, dict) else (out[0] if out else {})
        return (
            data.get("process", "Unknown"),
            float(data.get("confidence", 0.0) or 0.0),
            list(data.get("alternatives", [])),
        )
    except Exception:
        return "Unknown", 0.0, []


def lc_generate_checklist(process: str, context: str) -> List[Dict[str, Any]]:
    tmpl = (
        "From the ADGM context and process '{process}', produce the required documents checklist.\n"
        "Return strict JSON list of items: {{name, rationale, source_url}}. Keep 3-8 items.\n\n"
        "Context:\n{context}"
    )
    try:
        return _run_json_list(tmpl, process=process, context=context[:4000])
    except Exception:
        return []


def lc_segment_clauses(text: str) -> List[Dict[str, Any]]:
    tmpl = (
        "Segment the document into clauses with types. Return strict JSON list: {type, heading, start_hint, text}.\n"
        "Types examples: jurisdiction, execution/signature, governing_law, meetings, directors.\n\n"
        "Document:\n{text}"
    )
    try:
        return _run_json_list(tmpl, text=text[:6000])
    except Exception:
        return []


def lc_summarize_doc(text: str) -> str:
    tmpl = (
        "Provide a 2-3 sentence executive summary of the document content, focusing on ADGM (Abu Dhabi Global Market) context.\n\n"
        "Document (truncated):\n{text}\n\n"
        "Summary:"
    )
    return _run_text(tmpl, text=text[:3000])


def heuristic_summarize(text: str) -> str:
    """Offline fallback summarizer: returns 1-2 sentences from the start, trimmed."""
    if not text:
        return ""
    import re
    snippet = text.strip()
    # split into sentences (very rough)
    parts = re.split(r"(?<=[.!?])\s+", snippet)
    summary = " ".join(parts[:2]).strip()
    if len(summary) > 400:
        summary = summary[:397] + "..."
    return summary or snippet[:300]


def lc_checklist_summary(process: str, uploaded: int, required: int, missing: List[str]) -> str:
    tmpl = (
        "Write a concise user-facing summary about checklist completeness for process '{process}'.\n"
        "Include counts and list missing items, if any. Be factual and brief.\n"
        "Return 1-2 sentences.\n"
        "Inputs: uploaded={uploaded}, required={required}, missing={missing}"
    )
    return _run_text(tmpl, process=process, uploaded=uploaded, required=required, missing=", ".join(missing))


def lc_expand_queries(text: str) -> List[str]:
    tmpl = (
        "Given a clause, generate 2-3 concise search queries to retrieve relevant ADGM regulations/articles.\n"
        "Return strict JSON list of strings.\n\nClause:\n{text}"
    )
    try:
        return [q for q in _run_json_list(tmpl, text=text[:1200]) if isinstance(q, str)]
    except Exception:
        return []


