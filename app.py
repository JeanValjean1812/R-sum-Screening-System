"""Streamlit web interface for the résumé screening system.

Paste a job description, upload one or more résumés (PDF / DOCX / TXT) and get an
objective, ranked leaderboard. The heavy lifting is delegated to the same
multiprocessing pipeline used by the command line (``main.screen_resumes``).

Run locally with:

    streamlit run app.py
"""

from __future__ import annotations

import multiprocessing as mp
import tempfile
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from main import (
    DEFAULT_TAXONOMY,
    load_config,
    parse_job_description,
    screen_resumes,
)

ROOT = Path(__file__).resolve().parent
SAMPLE_JD_DIR = ROOT / "samples" / "job_descriptions"


# --------------------------------------------------------------------- helpers
def _load_sample_jds() -> dict:
    """Map a friendly name -> sample job-description text."""
    samples = {}
    if SAMPLE_JD_DIR.exists():
        for path in sorted(SAMPLE_JD_DIR.glob("*.txt")):
            label = path.stem.replace("_", " ").title()
            samples[label] = path.read_text(encoding="utf-8")
    return samples


def _save_uploads(uploaded_files, directory: Path) -> List[Path]:
    """Persist uploaded files to a temp directory so workers can read them by path."""
    paths: List[Path] = []
    for uploaded in uploaded_files:
        dest = directory / uploaded.name
        dest.write_bytes(uploaded.getbuffer())
        paths.append(dest)
    return paths


# ------------------------------------------------------------------- page setup
st.set_page_config(page_title="Résumé Screening System", page_icon="📄", layout="wide")
st.title("📄 Résumé Screening System")
st.caption(
    "Rank candidates objectively against a job description — powered by Python "
    "and multiprocessing."
)

config = load_config()
sample_jds = _load_sample_jds()

# ------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    max_workers = mp.cpu_count()
    workers = st.slider("Parallel workers", 1, max(max_workers, 1), max(max_workers, 1))
    top_n = st.number_input("Show top N (0 = all)", min_value=0, value=0, step=1)
    st.markdown("---")
    st.subheader("Scoring weights")
    for label, weight in config["weights"].items():
        st.write(f"- **{label.replace('_', ' ').title()}**: {int(weight * 100)}%")
    st.markdown("---")
    st.caption("Tip: drop your own CV in to see how it scores against a role.")

# ------------------------------------------------------------------- JD input
col_jd, col_files = st.columns(2)

with col_jd:
    st.subheader("1. Job description")
    default_text = ""
    if sample_jds:
        choice = st.selectbox(
            "Start from a sample (optional):",
            ["— None —"] + list(sample_jds.keys()),
        )
        if choice != "— None —":
            default_text = sample_jds[choice]
    jd_text = st.text_area("Paste the job description here:", value=default_text, height=320)

with col_files:
    st.subheader("2. Résumés")
    uploaded_files = st.file_uploader(
        "Upload résumé files:",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )
    st.write(f"{len(uploaded_files) if uploaded_files else 0} file(s) selected.")

# ------------------------------------------------------------------- run
if st.button("🚀 Screen Résumés", type="primary"):
    if not jd_text.strip():
        st.error("Please provide a job description.")
    elif not uploaded_files:
        st.error("Please upload at least one résumé.")
    else:
        with st.spinner("Parsing and scoring résumés..."):
            jd = parse_job_description(
                jd_text, DEFAULT_TAXONOMY, config.get("keywords", {}).get("top_n", 15)
            )
            with tempfile.TemporaryDirectory() as tmp:
                resume_paths = _save_uploads(uploaded_files, Path(tmp))
                results = screen_resumes(
                    resume_paths, jd, config=config, workers=workers
                )

        if not results:
            st.warning("No résumés could be scored.")
        else:
            st.success(f"Screened {len(results)} résumé(s).")

            # What the job description asked for.
            with st.expander("What the system extracted from the job description"):
                st.write("**Required skills:**", ", ".join(sorted(jd.required_skills)) or "—")
                st.write("**Preferred skills:**", ", ".join(sorted(jd.preferred_skills)) or "—")
                st.write("**Minimum experience (years):**", jd.min_years or "Not specified")

            shown = results[: top_n or len(results)]

            # Leaderboard table.
            table = pd.DataFrame(
                [
                    {
                        "Rank": c.rank,
                        "Candidate": c.name,
                        "Score": c.total_score,
                        "Experience (yrs)": c.experience_years,
                        "Matched skills": c.matched_summary(limit=8),
                    }
                    for c in shown
                ]
            ).set_index("Rank")
            st.subheader("🏆 Leaderboard")
            st.dataframe(table, use_container_width=True)

            # Score bar chart.
            chart_df = pd.DataFrame(
                {"Candidate": [c.name for c in shown], "Score": [c.total_score for c in shown]}
            ).set_index("Candidate")
            st.bar_chart(chart_df)

            # Per-candidate breakdown.
            st.subheader("🔍 Score breakdown")
            for c in shown:
                with st.expander(f"#{c.rank} — {c.name} ({c.total_score:.2f}/100)"):
                    st.bar_chart(pd.DataFrame.from_dict(c.breakdown, orient="index", columns=["points"]))
                    st.write("**Required matched:**", ", ".join(sorted(c.required_matched)) or "—")
                    st.write("**Preferred matched:**", ", ".join(sorted(c.preferred_matched)) or "—")

            # Download.
            csv = pd.DataFrame(
                [
                    {
                        "rank": c.rank,
                        "name": c.name,
                        "file": c.file_name,
                        "score": c.total_score,
                        "experience_years": c.experience_years,
                        "required_matched": ", ".join(sorted(c.required_matched)),
                        "preferred_matched": ", ".join(sorted(c.preferred_matched)),
                    }
                    for c in results
                ]
            ).to_csv(index=False)
            st.download_button("⬇️ Download results (CSV)", csv, "results.csv", "text/csv")
