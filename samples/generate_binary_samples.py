"""Generate the binary (PDF / DOCX) sample résumés.

The repository ships a couple of résumés in PDF and DOCX format (in addition to
the plain-text ones) so the parser is exercised on every supported format out of
the box. Those binary files are committed, so you normally do **not** need to run
this script — it is provided for transparency and so the samples can be
regenerated.

Usage:
    pip install -r requirements-dev.txt
    python samples/generate_binary_samples.py
"""

from __future__ import annotations

from pathlib import Path

RESUME_DIR = Path(__file__).resolve().parent / "resumes"

# Candidate résumés rendered to binary formats (kept here so this script is
# self-contained and reproducible).
ALICE_PDF = """Alice Johnson
Senior Backend Engineer
alice.johnson@example.com | San Francisco, CA

Summary
Senior backend engineer with 6 years of professional Python development building
scalable web applications and REST APIs.

Skills
Python, Django, REST APIs, SQL, PostgreSQL, Docker, AWS, Git, Linux, CI/CD

Experience
Senior Backend Engineer - CloudWorks (2020 - Present)
- Designed and built REST APIs in Python and Django serving 5M+ users
- Deployed services on AWS using Docker containers
- Optimised PostgreSQL queries and database schemas

Software Engineer - DataPipe (2018 - 2020)
- Built backend web applications in Python
- Wrote automated tests and maintained CI/CD pipelines

Education
B.Sc. in Computer Science
"""

CAROL_DOCX = """Carol Davis
Backend Developer
carol.davis@example.com | Remote

Summary
Backend developer with 3 years of professional Python development experience,
focused on building and maintaining web applications and REST APIs.

Skills
Python, Django, REST APIs, SQL, MySQL, Git, Linux

Experience
Backend Developer - FinTechly (2021 - Present)
- Developed and maintained REST APIs using Python and Django
- Built web applications backed by MySQL databases
- Collaborated with frontend teams to deliver features

Education
B.Sc. in Software Engineering
"""


def write_pdf(text: str, path: Path) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_margin(15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.splitlines():
        # ``multi_cell`` wraps long lines; empty lines become blank paragraphs.
        pdf.multi_cell(pdf.epw, 6, line if line else " ")
    pdf.output(str(path))


def write_docx(text: str, path: Path) -> None:
    from docx import Document

    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(str(path))


def main() -> None:
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    write_pdf(ALICE_PDF, RESUME_DIR / "alice_johnson.pdf")
    write_docx(CAROL_DOCX, RESUME_DIR / "carol_davis.docx")
    print(f"Wrote alice_johnson.pdf and carol_davis.docx to {RESUME_DIR}")


if __name__ == "__main__":
    main()
