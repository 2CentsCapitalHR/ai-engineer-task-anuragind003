from __future__ import annotations

from typing import List
import os

from app.models.schemas import IssueItem, IssueEvidence
from app.services.retriever import FaissRetriever
from app.services.chains import lc_segment_clauses, lc_expand_queries
from app.core.config import get_settings
from app.core.llm import get_llm_client


PROMPT = (
    "You are an ADGM legal compliance assistant. Given a clause and retrieved ADGM references, "
    "identify red flags, cite the exact ADGM regulation snippet, assign severity (High/Medium/Low), "
    "and suggest compliant wording (short + long variant) if relevant. Respond in strict JSON list of issues with keys: "
    "document, section, issue, severity, category, groundedness (0..1), evidence:[{ref_id,snippet,source_url}], suggestion, suggestion_long. "
    "Ensure the citation is the best match (law/article) and grounded to the claim."
)


def _heuristic_issues(file_name: str, display_name: str, text: str, retriever: FaissRetriever) -> List[IssueItem]:
    issues: List[IssueItem] = []
    used_refs: set[str] = set()

    def cite(query: str):
        hits = retriever.search(query)
        for h in hits:
            ref_id = h.get("ref_id", "")
            if ref_id and ref_id not in used_refs:
                used_refs.add(ref_id)
                return [IssueEvidence(ref_id=ref_id, snippet=h.get("chunk", "")[:400], source_url=h.get("source_url"))]
        # fallback if all duplicates
        if hits:
            h = hits[0]
            return [IssueEvidence(ref_id=h.get("ref_id", ""), snippet=h.get("chunk", "")[:400], source_url=h.get("source_url"))]
        return []

    lower = text.lower()
    if "jurisdiction" in lower or "federal" in lower or "uae courts" in lower or "abu dhabi courts" in lower:
        issues.append(
            IssueItem(
                document=display_name,
                section="",
                issue="Jurisdiction references non-ADGM courts.",
                severity="High",
                evidence=cite("ADGM jurisdiction courts Companies Regulations article jurisdiction courts"),
                suggestion=(
                    "Specify ADGM Courts as the governing jurisdiction. Suggested clause: "
                    "'This Agreement shall be governed by the laws of the Abu Dhabi Global Market (ADGM), and the courts of ADGM shall have exclusive jurisdiction.'"
                ),
                source_filename=file_name,
            )
        )
    if "signature" not in lower and "signed" not in lower:
        issues.append(
            IssueItem(
                document=display_name,
                section="",
                issue="Missing explicit signatory section.",
                severity="Medium",
                evidence=cite("ADGM execution signature requirements signatory section"),
                suggestion=(
                    "Add signatory block with name, title, date, and authorized signature. Example: "
                    "'Signed for and on behalf of the Company by: Name: __________  Title: __________  Date: __________  Signature: __________'"
                ),
                source_filename=file_name,
            )
        )
    if "adgm" not in lower:
        issues.append(
            IssueItem(
                document=display_name,
                section="",
                issue="Document does not explicitly reference ADGM.",
                severity="Low",
                evidence=cite("ADGM Companies Regulations reference incorporation under ADGM"),
                suggestion=(
                    "Add a clause clarifying ADGM incorporation. Suggested wording: "
                    "'The Company is incorporated and existing under the Abu Dhabi Global Market (ADGM) Companies Regulations.'"
                ),
                source_filename=file_name,
            )
        )
    return issues


def check_compliance(file_name: str, display_name: str, text: str) -> List[IssueItem]:
    settings = get_settings()
    retriever = FaissRetriever(top_k=4)
    llm = get_llm_client()
    if llm is None:
        return _heuristic_issues(file_name, display_name, text, retriever)

    # Clause segmentation for targeted checks
    clauses = lc_segment_clauses(text)
    segments = [c.get("text", "") for c in clauses] or [text]
    issues_all: List[IssueItem] = []
    for seg in segments:
        # Query expansion improves retrieval
        queries = [seg[:300]] + lc_expand_queries(seg)
        hits = []
        for q in queries[:3]:
            try:
                hits.extend(retriever.search(q))
            except Exception:
                pass
        # unique and truncate
        seen = set()
        ctx_hits = []
        for h in hits:
            key = h.get("ref_id")
            if key and key not in seen:
                seen.add(key)
                ctx_hits.append(h)
            if len(ctx_hits) >= 6:
                break
        context = "\n\n".join([f"[{h['ref_id']}] {h['chunk']}\n(Source: {h.get('source_url') or h.get('title')})" for h in ctx_hits])

        prompt = f"{PROMPT}\n\nClause:\n{seg[:4000]}\n\nReferences:\n{context}\n"
        try:
            # Expect JSON list; if not, skip this segment
            data = llm.generate_json_list(prompt)
            for item in data:
                ev = [IssueEvidence(ref_id=e.get("ref_id", ""), snippet=e.get("snippet", ""), source_url=e.get("source_url")) for e in item.get("evidence", [])]
                issues_all.append(
                    IssueItem(
                        document=item.get("document", display_name) or display_name,
                        section=item.get("section", ""),
                        issue=item.get("issue", ""),
                        severity=item.get("severity", "Medium"),
                        evidence=ev,
                        suggestion=item.get("suggestion"),
                        suggestion_long=item.get("suggestion_long"),
                        category=item.get("category"),
                        groundedness=item.get("groundedness"),
                        source_filename=file_name,
                    )
                )
        except Exception:
            continue
    if issues_all:
        return issues_all
    return _heuristic_issues(file_name, display_name, text, retriever)
