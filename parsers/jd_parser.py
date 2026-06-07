"""Job-description parser.

Turns a free-text job description into a structured :class:`JDRequirements`
object: required skills, preferred skills, a minimum-experience figure and a set
of generic domain keywords. These four pieces map directly onto the four
components of the scoring formula.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set

from extractors.keyword_extractor import KeywordExtractor

# Headings that introduce the "required" and "preferred" sections of a JD.
_REQUIRED_HEADINGS = ["required skills", "requirements", "must have", "must-have", "qualifications"]
_PREFERRED_HEADINGS = ["preferred skills", "nice to have", "nice-to-have", "bonus", "preferred", "plus"]
# Any heading that ends a section we are capturing.
_ALL_HEADINGS = _REQUIRED_HEADINGS + _PREFERRED_HEADINGS + [
    "experience", "responsibilities", "about", "benefits", "what you", "we offer",
]


@dataclass
class JDRequirements:
    """Structured representation of a job description."""

    required_skills: Set[str] = field(default_factory=set)
    preferred_skills: Set[str] = field(default_factory=set)
    min_years: int = 0
    keywords: Set[str] = field(default_factory=set)
    raw_text: str = ""


class JDParser:
    """Parses a job description into structured requirements."""

    def __init__(self, keyword_extractor: KeywordExtractor) -> None:
        self.extractor = keyword_extractor

    def parse(self, jd_text: str, top_keywords: int = 15) -> JDRequirements:
        required_section = self._extract_section(jd_text, _REQUIRED_HEADINGS)
        preferred_section = self._extract_section(jd_text, _PREFERRED_HEADINGS)

        # Required skills: prefer the explicit section, otherwise scan the whole JD
        # so that even an unstructured description still yields requirements.
        required_skills = self.extractor.extract_skills(required_section)
        if not required_skills:
            required_skills = self.extractor.extract_skills(jd_text)

        preferred_skills = self.extractor.extract_skills(preferred_section)
        # A skill should never count as both required and preferred.
        preferred_skills -= required_skills

        min_years = self.extractor.extract_experience_years(jd_text)
        keywords = self.extractor.extract_keywords(jd_text, top_n=top_keywords)

        return JDRequirements(
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            min_years=min_years,
            keywords=keywords,
            raw_text=jd_text,
        )

    @staticmethod
    def _extract_section(text: str, headings: List[str]) -> str:
        """Return the lines that follow one of ``headings`` up to the next heading."""
        lines = text.splitlines()
        captured: List[str] = []
        capturing = False

        for line in lines:
            stripped = line.strip().lower().rstrip(":")

            if not capturing and any(stripped.startswith(h) for h in headings):
                capturing = True
                continue

            if capturing:
                # Stop when we hit the next section heading.
                if any(stripped.startswith(h) for h in _ALL_HEADINGS) and stripped:
                    break
                captured.append(line)

        return "\n".join(captured)
