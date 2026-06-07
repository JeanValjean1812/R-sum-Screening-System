"""Scoring engine.

Applies a transparent, weighted formula to rank candidates objectively:

    Total Score = (Required Skills × 50%)
                + (Preferred Skills × 25%)
                + (Experience      × 15%)
                + (Keywords        × 10%)

Each component is a 0..1 *coverage ratio* (how much of what the job asks for is
present in the résumé), so the final score is naturally bounded to 0..100.
Because every résumé is measured against the same rubric, the ranking does not
depend on writing style or formatting — which is what helps reduce bias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

from parsers.jd_parser import JDRequirements


@dataclass
class CandidateScore:
    """The result of scoring one résumé against one job description."""

    name: str
    file_name: str
    total_score: float
    experience_years: int
    required_matched: Set[str] = field(default_factory=set)
    preferred_matched: Set[str] = field(default_factory=set)
    keywords_matched: Set[str] = field(default_factory=set)
    breakdown: Dict[str, float] = field(default_factory=dict)
    rank: int = 0

    def matched_summary(self, limit: int = 5) -> str:
        """A short, human-readable list of the strongest matched skills."""
        skills = sorted(self.required_matched) + sorted(self.preferred_matched)
        if not skills:
            return "—"
        shown = skills[:limit]
        suffix = f" (+{len(skills) - limit} more)" if len(skills) > limit else ""
        return ", ".join(shown) + suffix


class Scorer:
    """Computes weighted match scores for résumés."""

    def __init__(self, config: dict) -> None:
        self.weights: Dict[str, float] = config["weights"]
        self.default_target_years: int = config.get("experience", {}).get(
            "default_target_years", 3
        )

    def score(
        self,
        *,
        name: str,
        file_name: str,
        resume_text: str,
        resume_skills: Set[str],
        resume_years: int,
        jd: JDRequirements,
        keyword_matcher,
    ) -> CandidateScore:
        """Score a single résumé against the parsed job description."""
        # 1. Required skills coverage.
        req_total = len(jd.required_skills)
        req_matched = jd.required_skills & resume_skills
        req_ratio = len(req_matched) / req_total if req_total else 0.0

        # 2. Preferred skills coverage.
        pref_total = len(jd.preferred_skills)
        pref_matched = jd.preferred_skills & resume_skills
        pref_ratio = len(pref_matched) / pref_total if pref_total else 0.0

        # 3. Experience coverage (capped at 100%). When the JD states no explicit
        #    requirement we measure against a configurable soft target instead, so
        #    that more experienced candidates are still rewarded.
        target_years = jd.min_years if jd.min_years > 0 else self.default_target_years
        exp_ratio = min(resume_years / target_years, 1.0) if target_years else 0.0

        # 4. Generic keyword / domain-familiarity coverage.
        key_total = len(jd.keywords)
        key_matched = keyword_matcher(resume_text, jd.keywords)
        key_ratio = len(key_matched) / key_total if key_total else 0.0

        breakdown = {
            "required_skills": round(req_ratio * self.weights["required_skills"] * 100, 2),
            "preferred_skills": round(pref_ratio * self.weights["preferred_skills"] * 100, 2),
            "experience": round(exp_ratio * self.weights["experience"] * 100, 2),
            "keywords": round(key_ratio * self.weights["keywords"] * 100, 2),
        }
        total_score = round(sum(breakdown.values()), 2)

        return CandidateScore(
            name=name,
            file_name=file_name,
            total_score=total_score,
            experience_years=resume_years,
            required_matched=req_matched,
            preferred_matched=pref_matched,
            keywords_matched=key_matched,
            breakdown=breakdown,
        )
