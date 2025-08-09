from __future__ import annotations

import os
import uuid
from typing import Dict, List

from app.models.schemas import AnalysisReport, IssueItem
from app.services.chains import lc_checklist_summary, lc_summarize_doc


def build_report(
    process: str,
    uploaded_doc_types: List[str],
    required_documents: int,
    missing_documents: List[str],
    issues: List[IssueItem],
    annotated_paths: Dict[str, str],
) -> AnalysisReport:
    task_id = str(uuid.uuid4())
    report = AnalysisReport(
        process=process,
        documents_uploaded=len(uploaded_doc_types),
        required_documents=required_documents,
        missing_documents=missing_documents,
        issues_found=issues,
        generated_files={
            "annotated_docx": ", ".join(os.path.basename(p) for p in annotated_paths.values()),
            "report_json": f"{task_id}.json",
        },
        task_id=task_id,
    )
    # Optional LLM checklist summary; ignore failures
    try:
        report.checklist_summary = lc_checklist_summary(
            process=process,
            uploaded=len(uploaded_doc_types),
            required=required_documents,
            missing=missing_documents,
        )
    except Exception:
        pass
    return report
