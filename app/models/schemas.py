from __future__ import annotations

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class IssueEvidence(BaseModel):
    ref_id: str = Field(...)
    snippet: str = Field(...)
    source_url: Optional[str] = Field(default=None)


class IssueItem(BaseModel):
    document: str = Field(...)
    section: str = Field(default="")
    issue: str = Field(...)
    severity: str = Field(default="Medium")
    evidence: List[IssueEvidence] = Field(default_factory=list)
    suggestion: Optional[str] = None
    source_filename: Optional[str] = None
    category: Optional[str] = None
    groundedness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    suggestion_long: Optional[str] = None


class ChecklistResult(BaseModel):
    process: str
    documents_uploaded: int
    required_documents: int
    missing_documents: List[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    process: str
    documents_uploaded: int
    required_documents: int
    missing_documents: List[str]
    issues_found: List[IssueItem]
    generated_files: Dict[str, str]
    task_id: str
    checklist_items: List["ChecklistItem"] = Field(default_factory=list)
    process_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    checklist_summary: Optional[str] = None
    doc_summaries: Dict[str, str] = Field(default_factory=dict)


class ChecklistItem(BaseModel):
    name: str
    rationale: Optional[str] = None
    source_url: Optional[str] = None
    present: bool = False


class IntakeDoc(BaseModel):
    filename: str
    doc_type: str
    text: str
    # Optionally store embeddings or metadata later


class IntakeResult(BaseModel):
    docs: List[IntakeDoc]


class WorkflowResult(BaseModel):
    report: AnalysisReport
    annotated_paths: Dict[str, str]
