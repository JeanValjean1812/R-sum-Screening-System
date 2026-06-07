"""Command-line résumé screening with multiprocessing.

This module is the heart of the project. It wires the parser, extractor and
scorer together and uses a :class:`multiprocessing.Pool` to screen many résumés
in parallel — one worker process per CPU core — so a folder of hundreds of
résumés can be ranked in seconds.

Run ``python main.py --help`` for all options.

Design notes for multiprocessing
---------------------------------
* :func:`process_resume` is a *module-level* function so it can be pickled and
  sent to worker processes (required on the ``spawn`` start method used by
  Windows and macOS).
* Heavy, reusable objects (the taxonomy-backed extractor, the scorer) are built
  **once per worker** via the pool ``initializer`` instead of once per résumé.
* The CLI lives under ``if __name__ == "__main__"`` so importing this module
  (e.g. from ``app.py``) never spawns processes or runs the CLI.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from extractors.keyword_extractor import KeywordExtractor
from matcher.scorer import CandidateScore, Scorer
from parsers.jd_parser import JDParser, JDRequirements
from parsers.resume_parser import ResumeParser

# --------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_CONFIG = DATA_DIR / "config.json"
DEFAULT_TAXONOMY = DATA_DIR / "skills_taxonomy.json"
DEFAULT_RESUME_DIR = ROOT / "samples" / "resumes"
DEFAULT_JD = ROOT / "samples" / "job_descriptions" / "senior_python_developer.txt"
OUTPUT_DIR = ROOT / "output"

SUPPORTED_GLOBS = ("*.pdf", "*.docx", "*.txt")


# ------------------------------------------------------------ shared helpers
def load_config(config_path: Path | str = DEFAULT_CONFIG) -> dict:
    """Load the scoring configuration (weights, experience target, ...)."""
    with open(config_path, encoding="utf-8") as file:
        return json.load(file)


def parse_job_description(
    jd_text: str,
    taxonomy_path: Path | str = DEFAULT_TAXONOMY,
    top_keywords: int = 15,
) -> JDRequirements:
    """Parse raw job-description text into structured requirements."""
    extractor = KeywordExtractor(taxonomy_path)
    return JDParser(extractor).parse(jd_text, top_keywords=top_keywords)


def gather_resume_files(directory: Path | str) -> List[Path]:
    """Return every supported résumé file inside ``directory`` (sorted)."""
    directory = Path(directory)
    files: List[Path] = []
    for pattern in SUPPORTED_GLOBS:
        files.extend(directory.glob(pattern))
    return sorted(files)


def _score_one(
    file_path: Path,
    jd: JDRequirements,
    parser: ResumeParser,
    extractor: KeywordExtractor,
    scorer: Scorer,
) -> Optional[CandidateScore]:
    """Parse, extract and score a single résumé. Returns ``None`` on failure."""
    try:
        text = parser.parse(file_path)
        skills = extractor.extract_skills(text)
        years = extractor.extract_experience_years(text)
        name = parser.guess_name(text, file_path)
        return scorer.score(
            name=name,
            file_name=file_path.name,
            resume_text=text,
            resume_skills=skills,
            resume_years=years,
            jd=jd,
            keyword_matcher=extractor.count_keyword_matches,
        )
    except Exception as exc:  # noqa: BLE001 - one bad file shouldn't stop the run
        print(f"  ! Skipped {file_path.name}: {exc}", file=sys.stderr)
        return None


# ------------------------------------------------------ multiprocessing worker
# Per-process components, populated once by the pool initializer.
_WORKER: Dict[str, object] = {}


def _init_worker(taxonomy_path: str, config: dict) -> None:
    """Pool initializer: build the heavy components once per worker process."""
    _WORKER["parser"] = ResumeParser()
    _WORKER["extractor"] = KeywordExtractor(taxonomy_path)
    _WORKER["scorer"] = Scorer(config)


def process_resume(file_path: Path, jd: JDRequirements) -> Optional[CandidateScore]:
    """Top-level worker function: score one résumé using per-worker components."""
    return _score_one(
        file_path,
        jd,
        _WORKER["parser"],          # type: ignore[arg-type]
        _WORKER["extractor"],       # type: ignore[arg-type]
        _WORKER["scorer"],          # type: ignore[arg-type]
    )


# ------------------------------------------------------------------ pipeline
def screen_resumes(
    resume_files: Sequence[Path],
    jd: JDRequirements,
    *,
    taxonomy_path: Path | str = DEFAULT_TAXONOMY,
    config: Optional[dict] = None,
    workers: Optional[int] = None,
    use_multiprocessing: bool = True,
) -> List[CandidateScore]:
    """Screen and rank a collection of résumés against a job description.

    Parameters
    ----------
    resume_files:
        Paths to the résumé files to score.
    jd:
        Parsed job-description requirements.
    workers:
        Number of worker processes (defaults to the CPU count, capped at the
        number of résumés). ``1`` forces sequential processing.
    use_multiprocessing:
        Set to ``False`` to run sequentially (useful for benchmarking/debugging
        or on single-core hosts).
    """
    config = config or load_config()
    taxonomy_path = str(taxonomy_path)
    files = list(resume_files)
    if not files:
        return []

    worker_count = workers or mp.cpu_count()
    worker_count = max(1, min(worker_count, len(files)))

    results: List[CandidateScore] = []

    if use_multiprocessing and worker_count > 1:
        try:
            with mp.Pool(
                processes=worker_count,
                initializer=_init_worker,
                initargs=(taxonomy_path, config),
            ) as pool:
                worker = partial(process_resume, jd=jd)
                for result in pool.imap_unordered(worker, files):
                    if result is not None:
                        results.append(result)
        except Exception as exc:  # noqa: BLE001 - fall back to sequential
            print(
                f"  ! Multiprocessing unavailable ({exc}); running sequentially.",
                file=sys.stderr,
            )
            results = _screen_sequential(files, jd, taxonomy_path, config)
    else:
        results = _screen_sequential(files, jd, taxonomy_path, config)

    # Rank by score (highest first); break ties alphabetically for stability.
    results.sort(key=lambda r: (-r.total_score, r.name))
    for index, result in enumerate(results, start=1):
        result.rank = index
    return results


def _screen_sequential(
    files: Sequence[Path],
    jd: JDRequirements,
    taxonomy_path: str,
    config: dict,
) -> List[CandidateScore]:
    parser = ResumeParser()
    extractor = KeywordExtractor(taxonomy_path)
    scorer = Scorer(config)
    scored = [_score_one(f, jd, parser, extractor, scorer) for f in files]
    return [s for s in scored if s is not None]


# ------------------------------------------------------------------- output
def format_leaderboard(results: Sequence[CandidateScore], top: Optional[int] = None) -> str:
    """Render the ranked results in the article's leaderboard style."""
    shown = results[:top] if top else results
    lines = ["=" * 60, "SCREENING RESULTS", "=" * 60]
    if not shown:
        lines.append("No résumés were scored.")
    for candidate in shown:
        lines.append(
            f"Rank #{candidate.rank}: {candidate.name} | "
            f"Score: {candidate.total_score:.2f}/100 | "
            f"Matched: {candidate.matched_summary()}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def save_results(results: Sequence[CandidateScore], output_dir: Path | str = OUTPUT_DIR) -> Path:
    """Write the ranked results to a CSV file and return its path."""
    import pandas as pd  # imported here so the core pipeline stays import-light

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "rank": c.rank,
            "name": c.name,
            "file": c.file_name,
            "score": c.total_score,
            "experience_years": c.experience_years,
            "required_matched": ", ".join(sorted(c.required_matched)),
            "preferred_matched": ", ".join(sorted(c.preferred_matched)),
            "required_pts": c.breakdown.get("required_skills"),
            "preferred_pts": c.breakdown.get("preferred_skills"),
            "experience_pts": c.breakdown.get("experience"),
            "keywords_pts": c.breakdown.get("keywords"),
        }
        for c in results
    ]
    out_path = output_dir / "results.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    return out_path


# --------------------------------------------------------------------- CLI
def _read_jd(args: argparse.Namespace) -> str:
    if args.jd_text:
        return args.jd_text
    jd_path = Path(args.jd)
    if not jd_path.exists():
        sys.exit(f"Job description file not found: {jd_path}")
    return jd_path.read_text(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Screen and rank résumés against a job description using multiprocessing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-r", "--resumes", default=str(DEFAULT_RESUME_DIR),
                        help="Folder containing résumé files (.pdf/.docx/.txt).")
    parser.add_argument("-j", "--jd", default=str(DEFAULT_JD),
                        help="Path to a job-description file.")
    parser.add_argument("--jd-text", default=None,
                        help="Inline job-description text (overrides --jd).")
    parser.add_argument("-w", "--workers", type=int, default=None,
                        help="Number of worker processes (default: CPU count).")
    parser.add_argument("-n", "--top", type=int, default=None,
                        help="Only display the top N candidates.")
    parser.add_argument("--sequential", action="store_true",
                        help="Disable multiprocessing (useful for benchmarking).")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not write a results.csv file.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to config.json.")
    parser.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY),
                        help="Path to skills_taxonomy.json.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_arg_parser().parse_args(argv)
    config = load_config(args.config)

    jd_text = _read_jd(args)
    jd = parse_job_description(jd_text, args.taxonomy, config.get("keywords", {}).get("top_n", 15))

    resume_files = gather_resume_files(args.resumes)
    if not resume_files:
        sys.exit(f"No résumés (.pdf/.docx/.txt) found in: {args.resumes}")

    mode = "sequential" if args.sequential else f"{args.workers or mp.cpu_count()} workers"
    print(f"Screening {len(resume_files)} résumé(s) using {mode}...\n")

    start = time.perf_counter()
    results = screen_resumes(
        resume_files,
        jd,
        taxonomy_path=args.taxonomy,
        config=config,
        workers=args.workers,
        use_multiprocessing=not args.sequential,
    )
    elapsed = time.perf_counter() - start

    print(format_leaderboard(results, top=args.top))
    print(f"\nScreened {len(results)} résumé(s) in {elapsed:.3f}s.")

    if not args.no_save and results:
        out_path = save_results(results)
        print(f"Detailed results written to: {out_path}")


if __name__ == "__main__":
    main()
