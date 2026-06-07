"""Résumé parser: extracts plain text from PDF, DOCX and TXT files.

A single ``parse()`` entry point dispatches to a format-specific extractor based
on the file extension, so the rest of the pipeline only ever sees clean text and
never has to care about the original document format.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

# ``pypdf`` is the maintained successor of ``PyPDF2`` (same ``PdfReader`` API).
# We prefer it but fall back to ``PyPDF2`` so the project works with either.
try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - depends on which package is installed
    from PyPDF2 import PdfReader  # type: ignore

PathLike = Union[str, Path]

# A name line looks like 2-4 capitalised words (allows accented characters).
_NAME_RE = re.compile(
    r"^[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'.-]+(?:\s+[A-ZÀ-Ÿ][A-Za-zÀ-ÿ'.-]+){1,3}$"
)


class ResumeParser:
    """Extracts text from supported résumé formats."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def parse(self, file_path: PathLike) -> str:
        """Extract and return the plain text of a résumé file."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix == ".docx":
            return self._extract_docx(path)
        if suffix == ".txt":
            return self._extract_txt(path)

        raise ValueError(
            f"Unsupported file type: '{suffix}'. "
            f"Supported types: {sorted(self.SUPPORTED_EXTENSIONS)}"
        )

    # ------------------------------------------------------------ format readers
    def _extract_pdf(self, file_path: Path) -> str:
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()

    def _extract_docx(self, file_path: Path) -> str:
        from docx import Document  # imported lazily so PDF/TXT users needn't install it

        document = Document(str(file_path))
        return "\n".join(para.text for para in document.paragraphs).strip()

    def _extract_txt(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8", errors="ignore").strip()

    # ------------------------------------------------------------------- helpers
    @staticmethod
    def guess_name(text: str, file_path: PathLike) -> str:
        """Best-effort candidate name.

        Most résumés put the candidate's name on the first line, so we use the
        first line that looks like a name and otherwise fall back to a prettified
        version of the file name.
        """
        for line in text.splitlines():
            line = line.strip()
            if _NAME_RE.match(line):
                return line

        stem = Path(file_path).stem
        return stem.replace("_", " ").replace("-", " ").title()
