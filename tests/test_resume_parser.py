"""Tests for the résumé parser and the end-to-end screening pipeline."""

import pytest

from parsers.resume_parser import ResumeParser

import main


def test_parse_txt(tmp_path):
    f = tmp_path / "cv.txt"
    f.write_text("John Doe\nPython developer", encoding="utf-8")
    text = ResumeParser().parse(f)
    assert "Python developer" in text


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "cv.rtf"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        ResumeParser().parse(f)


def test_guess_name_from_first_line(tmp_path):
    f = tmp_path / "cv.txt"
    f.write_text("Jane Smith\nSoftware Engineer", encoding="utf-8")
    assert ResumeParser.guess_name(f.read_text(), f) == "Jane Smith"


def test_guess_name_falls_back_to_filename(tmp_path):
    f = tmp_path / "ada_lovelace.txt"
    f.write_text("curriculum vitae\nengineer", encoding="utf-8")
    assert ResumeParser.guess_name(f.read_text(), f) == "Ada Lovelace"


# --------------------------------------------------------------- integration
JD_TEXT = """Required Skills:
- Python
- Django
- SQL

Preferred Skills:
- Docker

Experience:
- 3+ years
"""


def _write_resume(directory, name, body):
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def test_pipeline_ranks_better_match_first_multiprocessing(tmp_path):
    strong = _write_resume(
        tmp_path, "strong.txt",
        "Strong Match\nPython Django SQL Docker, 5 years of experience",
    )
    weak = _write_resume(tmp_path, "weak.txt", "Weak Match\nKnows some HTML")

    jd = main.parse_job_description(JD_TEXT)
    results = main.screen_resumes(
        [strong, weak], jd, workers=2, use_multiprocessing=True
    )

    assert [r.rank for r in results] == [1, 2]
    assert results[0].name == "Strong Match"
    assert results[0].total_score > results[1].total_score


def test_sequential_and_parallel_agree(tmp_path):
    files = [
        _write_resume(tmp_path, "a.txt", "Alice A\nPython Django SQL, 4 years"),
        _write_resume(tmp_path, "b.txt", "Bob B\nPython, 1 year"),
        _write_resume(tmp_path, "c.txt", "Carol C\nDjango SQL Docker, 2 years"),
    ]
    jd = main.parse_job_description(JD_TEXT)

    parallel = main.screen_resumes(files, jd, workers=3, use_multiprocessing=True)
    sequential = main.screen_resumes(files, jd, use_multiprocessing=False)

    assert [r.name for r in parallel] == [r.name for r in sequential]
    assert [r.total_score for r in parallel] == [r.total_score for r in sequential]


def test_empty_folder_returns_empty(tmp_path):
    jd = main.parse_job_description(JD_TEXT)
    assert main.screen_resumes([], jd) == []
