"""Keyword and skill extraction from résumé / job-description text.

The extractor is deliberately dependency-free (standard library only) so it can
be cheaply re-created inside each worker process during multiprocessing.

Matching strategy
-----------------
* Text is lower-cased so matching is case-insensitive.
* Each skill in the taxonomy has a list of *variations* (e.g. ``"Power BI"`` may
  appear as ``"power bi"`` or ``"powerbi"``).
* Variations are matched using word boundaries (``\\b``) so that, for example,
  ``"Java"`` does **not** match inside ``"JavaScript"``.
* Matched canonical skill names are collected in a ``set`` to avoid duplicates.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Set

# Common English / résumé filler words that should never count as "keywords".
STOPWORDS: Set[str] = {
    "the", "and", "for", "are", "with", "you", "your", "our", "this", "that",
    "will", "have", "has", "had", "from", "they", "their", "them", "but", "not",
    "can", "all", "any", "who", "what", "when", "where", "which", "how", "why",
    "into", "out", "about", "over", "under", "more", "most", "such", "than",
    "then", "also", "able", "may", "must", "should", "would", "could", "we",
    "us", "as", "at", "by", "in", "on", "of", "to", "is", "be", "an", "a",
    "or", "it", "its", "if", "do", "does", "job", "role", "team", "work",
    "working", "looking", "candidate", "candidates", "years", "year", "etc",
    "including", "include", "includes", "experience", "skills", "required",
    "preferred", "responsibilities", "requirements", "ability", "strong",
    "good", "excellent", "plus", "knowledge", "understanding", "company",
    "position", "join", "help", "build", "using", "use", "well", "across",
}

# Matches "3+ years", "5 years", "10 yrs", "2-4 years" (captures the number(s)).
_YEARS_RE = re.compile(r"(\d+)\s*(?:-\s*(\d+))?\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)

# A "word" used when building the generic keyword list.
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./-]{2,}")


class KeywordExtractor:
    """Extracts canonical skills, experience and keywords from free text."""

    def __init__(self, taxonomy_path: Path | str) -> None:
        self.taxonomy_path = Path(taxonomy_path)
        self.skills_taxonomy: Dict[str, Dict[str, List[str]]] = self._load_taxonomy()

    def _load_taxonomy(self) -> Dict[str, Dict[str, List[str]]]:
        with open(self.taxonomy_path, encoding="utf-8") as file:
            return json.load(file)

    # ------------------------------------------------------------------ skills
    def extract_skills(self, text: str) -> Set[str]:
        """Return the set of canonical skill names found in ``text``."""
        text_lower = text.lower()
        found_skills: Set[str] = set()

        for _category, skills_dict in self.skills_taxonomy.items():
            for skill_name, variations in skills_dict.items():
                for variation in variations:
                    # Word boundaries prevent "Java" matching inside "JavaScript".
                    pattern = r"\b" + re.escape(variation.lower()) + r"\b"
                    if re.search(pattern, text_lower):
                        found_skills.add(skill_name)
                        break  # one variation is enough for this skill

        return found_skills

    # -------------------------------------------------------------- experience
    def extract_experience_years(self, text: str) -> int:
        """Return the largest "N years" figure mentioned in ``text`` (0 if none).

        For a range such as "2-4 years" the upper bound is used.
        """
        best = 0
        for match in _YEARS_RE.finditer(text):
            numbers = [int(group) for group in match.groups() if group]
            if numbers:
                best = max(best, max(numbers))
        return best

    # ---------------------------------------------------------------- keywords
    def extract_keywords(self, text: str, top_n: int = 15) -> Set[str]:
        """Return the ``top_n`` most frequent meaningful words in ``text``.

        These act as a soft "domain familiarity" signal that is distinct from the
        curated skills taxonomy.
        """
        words = [w.lower() for w in _WORD_RE.findall(text)]
        meaningful = [w for w in words if w not in STOPWORDS and len(w) > 3]
        counts = Counter(meaningful)
        return {word for word, _count in counts.most_common(top_n)}

    def count_keyword_matches(self, text: str, keywords: Iterable[str]) -> Set[str]:
        """Return which of ``keywords`` appear (as whole words) in ``text``."""
        text_lower = text.lower()
        matched: Set[str] = set()
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched.add(keyword)
        return matched
