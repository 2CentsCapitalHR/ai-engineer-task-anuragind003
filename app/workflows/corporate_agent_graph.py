from __future__ import annotations

import os
from typing import Dict, List, TypedDict
from langgraph.graph import StateGraph

from app.core.config import get_settings
from app.agents.doc_intake import run_doc_intake
from app.agents.process_identifier import detect_process, detect_process_from_texts
from app.agents.checklist_verifier import verify_checklist
from app.agents.compliance_checker import check_compliance
from app.agents.docx_annotator import annotate_docx
from app.agents.report_generator import build_report
from app.models.schemas import IssueItem, WorkflowResult
from app.services.chains import lc_detect_process
from app.services.chains import lc_summarize_doc, heuristic_summarize


class WorkflowState(TypedDict):
    file_paths: List[str]
    doc_types: List[str]
    process: str
    issues: List[IssueItem]
    annotated_paths: Dict[str, str]
    intake_cache: Dict[str, str]


def node_intake(state: WorkflowState) -> WorkflowState:
    intake = run_doc_intake(state["file_paths"])
    doc_types = [d.doc_type for d in intake.docs]
    state["doc_types"] = doc_types
    # cache filename→text for reuse
    state["intake_cache"] = {d.filename: d.text for d in intake.docs}
    return state


def node_process_id(state: WorkflowState) -> WorkflowState:
    # Prefer detected value if set via override; otherwise run detection
    if not state.get("process"):
        deduced = detect_process(state.get("doc_types", []))
        if deduced == "Unknown":
            # Use cached texts for heuristic fallback
            texts = list(state.get("intake_cache", {}).values())
            deduced = detect_process_from_texts(texts)
        state["process"] = deduced
    return state


def node_compliance(state: WorkflowState) -> WorkflowState:
    # Aggregate issues across docs using cached texts
    issues: List[IssueItem] = []
    texts = state.get("intake_cache", {})
    # Use detected doc types as display names where possible
    type_map = {os.path.basename(p): t for p, t in zip(state["file_paths"], state.get("doc_types", []))}
    for filename, text in texts.items():
        display = type_map.get(filename, filename)
        issues.extend(check_compliance(filename, display, text))
    state["issues"] = issues
    return state


def node_annotate(state: WorkflowState) -> WorkflowState:
    # annotate per uploaded filename
    annotated: Dict[str, str] = {}
    for in_path in state["file_paths"]:
        fname = os.path.basename(in_path)
        # match either by source filename or by display document falling back to filename
        matching = [i for i in state.get("issues", []) if (i.source_filename == fname) or (i.document == fname)]
        outp = annotate_docx(in_path, matching)
        annotated[fname] = outp
    state["annotated_paths"] = annotated
    return state


def build_graph() -> StateGraph:
    sg = StateGraph(WorkflowState)
    sg.add_node("intake", node_intake)
    sg.add_node("process_id", node_process_id)
    sg.add_node("compliance", node_compliance)
    sg.add_node("annotate", node_annotate)

    sg.set_entry_point("intake")
    sg.add_edge("intake", "process_id")
    sg.add_edge("process_id", "compliance")
    sg.add_edge("compliance", "annotate")
    return sg


def run_workflow(file_paths: List[str], target_process: str | None = None) -> WorkflowResult:
    state: WorkflowState = {
        "file_paths": file_paths,
        "doc_types": [],
        "process": target_process or "",
        "issues": [],
        "annotated_paths": {},
        "intake_cache": {},
    }
    graph = build_graph().compile()
    final_state: WorkflowState = graph.invoke(state)

    # LLM-based process detection with fallback to heuristic
    if final_state["process"]:
        process = final_state["process"]
        process_conf = None
    else:
        try:
            proc, conf, _ = lc_detect_process(final_state.get("doc_types", []), " ".join(final_state.get("doc_types", [])))
            if proc and proc != "Unknown":
                process = proc
                process_conf = conf
            else:
                # Try doc types heuristic then raw text heuristic
                process = detect_process(final_state.get("doc_types", []))
                if process == "Unknown":
                    process = detect_process_from_texts(list(final_state.get("intake_cache", {}).values()))
                process = process or "Unknown"
            process_conf = conf
        except Exception:
            process = detect_process(final_state.get("doc_types", []))
            if process == "Unknown":
                process = detect_process_from_texts(list(final_state.get("intake_cache", {}).values())) or "Unknown"
            process_conf = None

    checklist, checklist_items = verify_checklist(process, final_state.get("doc_types", []))

    report = build_report(
        process=process,
        uploaded_doc_types=final_state.get("doc_types", []),
        required_documents=checklist.required_documents,
        missing_documents=checklist.missing_documents,
        issues=final_state.get("issues", []),
        annotated_paths=final_state.get("annotated_paths", {}),
    )
    report.process_confidence = process_conf
    # Generate per-document summaries (best-effort)
    # Generate per-document summaries with LLM or heuristic fallback; ensure all uploaded docs get a summary
    summaries = {}
    texts = final_state.get("intake_cache", {})
    for fname, text in texts.items():
        added = False
        try:
            summaries[fname] = lc_summarize_doc(text)
            added = True
        except Exception:
            added = False
        if not added:
            try:
                summaries[fname] = heuristic_summarize(text)
            except Exception:
                summaries[fname] = ""
    report.doc_summaries = summaries
    # attach checklist items for richer UI
    report.checklist_items = checklist_items
    return WorkflowResult(report=report, annotated_paths=final_state.get("annotated_paths", {}))
