from __future__ import annotations

import os
import json
from typing import Dict, Any, List
import streamlit as st

from app.ui.streamlit_theme import CSS, PRIMARY, SECONDARY, ACCENT, DANGER, WARNING


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header() -> None:
    st.markdown(
        """
        <div class='hero'>
          <h2>ADGM Corporate Agent</h2>
          <div class='subtitle'>Multi-agent RAG review for ADGM documents — Gemini + FAISS + LangGraph</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def upload_section() -> List[str]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Upload .docx files")
    files = st.file_uploader("Drag & drop or browse", type=["docx"], accept_multiple_files=True)

    saved_paths: List[str] = []
    if files:
        upload_dir = st.session_state.get("upload_dir")
        os.makedirs(upload_dir, exist_ok=True)
        for f in files:
            dst = os.path.join(upload_dir, f.name)
            with open(dst, "wb") as out:
                out.write(f.read())
            saved_paths.append(dst)
        st.success(f"Uploaded {len(saved_paths)} file(s)")
    st.markdown("</div>", unsafe_allow_html=True)
    return saved_paths


def checklist_card(summary: Dict[str, Any]) -> None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Checklist Summary")
    cols = st.columns(3)
    cols[0].metric("Process", summary.get("process", "Unknown"))
    cols[1].metric("Uploaded", summary.get("documents_uploaded", 0))
    cols[2].metric("Required", summary.get("required_documents", 0))
    # Show process confidence if present
    conf = summary.get("process_confidence", None)
    if isinstance(conf, (int, float)):
        st.caption(f"Process confidence: {conf:.2f}")

    missing = summary.get("missing_documents", [])
    if missing:
        st.markdown("<div class='muted'>Missing</div>", unsafe_allow_html=True)
        for m in missing:
            st.markdown(f"<span class='chip warn'>{m}</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='chip ok'>All required documents present</span>", unsafe_allow_html=True)

    # Optional: show rationales and source links if present
    items = summary.get("checklist_items", [])
    if items:
        with st.expander("Checklist details"):
            for it in items:
                name = _get_value(it, "name")
                present = _get_value(it, "present", False)
                rationale = _get_value(it, "rationale", None)
                url = _get_value(it, "source_url", None)
                badge = "ok" if present else "danger"
                st.markdown(f"<span class='chip {badge}'>{name}</span>", unsafe_allow_html=True)
                if rationale or url:
                    txt = rationale or ""
                    if url:
                        st.write(f"{txt} (source: {url})")
                    else:
                        st.write(txt)
    # Optional LLM-generated summary if present
    if summary.get("checklist_summary"):
        st.info(str(summary["checklist_summary"]))
    st.markdown("</div>", unsafe_allow_html=True)


def checklist_summary_banner(summary: Dict[str, Any]) -> None:
    process = summary.get("process") or "Unknown"
    uploaded = int(summary.get("documents_uploaded", 0) or 0)
    required = int(summary.get("required_documents", 0) or 0)
    missing_list = summary.get("missing_documents", []) or []

    if not process or process == "Unknown":
        st.info(
            "We couldn't confidently detect the process. You can set one via the 'Process override' in the sidebar."
        )
        # Avoid implying completeness when process is unknown or required is zero
        if required == 0:
            st.caption("Checklist will appear once a process is detected.")
        return

    if missing_list:
        # Follow the example wording closely
        missing_display = ", ".join(missing_list)
        st.warning(
            f"It appears that you're trying to {process.lower()} in ADGM. "
            f"Based on our reference list, you have uploaded {uploaded} out of {required} required documents. "
            f"The missing document(s) appear to be: {missing_display}."
        )
    else:
        st.success(
            f"Detected process: {process}. All required documents are present ({uploaded}/{required})."
        )


def _get_value(item: Any, key: str, default: Any = "") -> Any:
    # Works with dicts and Pydantic models
    if isinstance(item, dict):
        return item.get(key, default)
    try:
        return getattr(item, key)
    except Exception:
        return default


def issues_table(issues: List[Any]) -> None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Issues Found")
    if not issues:
        st.info("No issues detected.")
    else:
        for i, it in enumerate(issues, 1):
            severity = _get_value(it, "severity", "Medium")
            document = _get_value(it, "document", "")
            section = _get_value(it, "section", "")
            issue = _get_value(it, "issue", "")
            suggestion = _get_value(it, "suggestion", None)
            suggestion_long = _get_value(it, "suggestion_long", None)
            category = _get_value(it, "category", None)
            groundedness = _get_value(it, "groundedness", None)
            evidence = _get_value(it, "evidence", [])

            sev_color = {"High": DANGER, "Medium": WARNING, "Low": ACCENT}.get(str(severity), ACCENT)
            cat_label = f" • {category}" if category else ""
            g_score = f" (groundedness: {groundedness:.2f})" if isinstance(groundedness, (int, float)) else ""
            st.markdown(
                f"<div style='border-left:4px solid {sev_color};padding-left:10px;margin-bottom:10px'>"
                f"<b>{i}. [{severity}]</b> {issue}{cat_label}{g_score}<br/>"
                f"<span class='muted'>{document} — {section}</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            if suggestion:
                st.caption("Suggestion: " + str(suggestion))
            if suggestion_long:
                with st.expander("Alternative wording (long)"):
                    st.write(str(suggestion_long))
            if evidence:
                with st.expander("Citations"):
                    for ev in evidence:
                        if isinstance(ev, dict):
                            ref_id = ev.get("ref_id", "")
                            snippet = ev.get("snippet", "")
                            src = ev.get("source_url", "")
                        else:
                            ref_id = getattr(ev, "ref_id", "")
                            snippet = getattr(ev, "snippet", "")
                            src = getattr(ev, "source_url", "")
                        st.code(f"{ref_id}: {snippet}")
                        if src:
                            st.caption(f"Source: {src}")
    st.markdown("</div>", unsafe_allow_html=True)


def summaries_table(summaries: Dict[str, str] | None) -> None:
    if not summaries:
        return
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Document Summaries")
    for fname, text in summaries.items():
        with st.expander(fname):
            st.write(text)
    st.markdown("</div>", unsafe_allow_html=True)


def downloads_section(files: List[str]) -> None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Reviewed Documents")
    if not files:
        st.info("No reviewed files yet.")
    else:
        for path in files:
            name = os.path.basename(path)
            with open(path, "rb") as f:
                st.download_button("Download " + name, f, file_name=name, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
