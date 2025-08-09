from __future__ import annotations

import os
import json
import sys
from typing import List
import streamlit as st

# Ensure project root in sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.config import get_settings
from app.workflows.corporate_agent_graph import run_workflow
from app.ui.streamlit_components import (
    inject_theme,
    header,
    upload_section,
    checklist_card,
    checklist_summary_banner,
    issues_table,
    summaries_table,
    downloads_section,
)


def main() -> None:
    settings = get_settings()
    st.set_page_config(
        page_title="ADGM Corporate Agent",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Theme
    inject_theme()
    header()

    # Sidebar config
    with st.sidebar:
        st.markdown("### Configuration")
        st.caption("Set paths and parameters")
        upload_dir = st.text_input("Upload dir", value=settings.upload_dir, key="cfg_upload_dir")
        output_dir = st.text_input("Output dir", value=settings.output_dir, key="cfg_output_dir")
        st.session_state["upload_dir"] = upload_dir
        st.session_state["output_dir"] = output_dir
        st.divider()
        st.caption("Index status")
        st.write(os.path.exists(settings.faiss_index_dir) and "FAISS index present" or "Index missing – run ingest")
        st.divider()
        st.caption("Process override (optional)")
        st.session_state["override_process"] = st.selectbox(
            "Process",
            options=["", "Company Incorporation", "Licensing"],
            index=0,
            help="If unsure detection, force a process for checklist and review.",
        )

    # Tabs
    tab_upload, tab_review, tab_downloads = st.tabs(["Upload", "Review", "Downloads"])

    with tab_upload:
        file_paths: List[str] = upload_section()
        go = st.button("Analyze", type="primary")
        if go and file_paths:
            try:
                with st.spinner("Running multi-agent workflow..."):
                    result = run_workflow(file_paths, target_process=(st.session_state.get("override_process") or None))

                # Persist to session state
                st.session_state["report_dict"] = result.report.model_dump()
                st.session_state["issues_list"] = list(result.report.issues_found)

                # Write JSON report to output dir and include in downloads
                output_dir = st.session_state.get("output_dir") or get_settings().output_dir
                os.makedirs(output_dir, exist_ok=True)
                report_name = result.report.generated_files.get("report_json")
                if report_name:
                    report_path = os.path.join(output_dir, report_name)
                    with open(report_path, "w", encoding="utf-8") as f:
                        json.dump(result.report.model_dump(), f, ensure_ascii=False, indent=2)
                else:
                    report_path = None

                annotated_files = list(result.annotated_paths.values())
                if report_path:
                    annotated_files.append(report_path)
                st.session_state["annotated_files"] = annotated_files

                st.success("Analysis complete. Open the Review and Downloads tabs for results.")
            except RuntimeError as e:
                st.error(f"Analysis failed: {e}")

    with tab_review:
        report_dict = st.session_state.get("report_dict")
        issues = st.session_state.get("issues_list", [])
        if report_dict:
            checklist_summary_banner(report_dict)
            checklist_card(report_dict)
            summaries_table(report_dict.get("doc_summaries", {}))
            issues_table(issues)
        else:
            st.info("No analysis found. Upload and analyze documents first.")

    with tab_downloads:
        files = st.session_state.get("annotated_files", [])
        downloads_section(files)


if __name__ == "__main__":
    main()
