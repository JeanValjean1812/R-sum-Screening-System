"""Tests for the weighted scoring engine."""

from matcher.scorer import Scorer
from parsers.jd_parser import JDRequirements


def _make_jd():
    return JDRequirements(
        required_skills={"Python", "Django", "SQL"},
        preferred_skills={"Docker", "AWS"},
        min_years=3,
        keywords={"backend", "scalable"},
        raw_text="",
    )


def _no_keyword_matcher(_text, _keywords):
    return set()


def test_perfect_match_scores_100(config):
    scorer = Scorer(config)
    jd = _make_jd()
    result = scorer.score(
        name="Perfect Candidate",
        file_name="perfect.txt",
        resume_text="python django sql docker aws backend scalable",
        resume_skills={"Python", "Django", "SQL", "Docker", "AWS"},
        resume_years=5,
        jd=jd,
        keyword_matcher=lambda text, kws: set(kws),
    )
    assert result.total_score == 100.0


def test_empty_resume_scores_zero(config):
    scorer = Scorer(config)
    jd = _make_jd()
    result = scorer.score(
        name="Empty",
        file_name="empty.txt",
        resume_text="",
        resume_skills=set(),
        resume_years=0,
        jd=jd,
        keyword_matcher=_no_keyword_matcher,
    )
    assert result.total_score == 0.0


def test_required_skills_outweigh_preferred(config):
    """All required skills should beat all preferred skills, given equal everything else."""
    scorer = Scorer(config)
    jd = _make_jd()

    only_required = scorer.score(
        name="Req", file_name="r.txt", resume_text="", resume_skills={"Python", "Django", "SQL"},
        resume_years=0, jd=jd, keyword_matcher=_no_keyword_matcher,
    )
    only_preferred = scorer.score(
        name="Pref", file_name="p.txt", resume_text="", resume_skills={"Docker", "AWS"},
        resume_years=0, jd=jd, keyword_matcher=_no_keyword_matcher,
    )
    assert only_required.total_score > only_preferred.total_score


def test_breakdown_sums_to_total(config):
    scorer = Scorer(config)
    jd = _make_jd()
    result = scorer.score(
        name="X", file_name="x.txt", resume_text="python",
        resume_skills={"Python", "Docker"}, resume_years=2, jd=jd,
        keyword_matcher=lambda text, kws: {"backend"},
    )
    assert round(sum(result.breakdown.values()), 2) == result.total_score


def test_experience_is_capped(config):
    """Years far above the requirement should not exceed the experience weight."""
    scorer = Scorer(config)
    jd = _make_jd()
    result = scorer.score(
        name="Veteran", file_name="v.txt", resume_text="",
        resume_skills=set(), resume_years=40, jd=jd, keyword_matcher=_no_keyword_matcher,
    )
    # experience weight is 15% -> at most 15 points.
    assert result.breakdown["experience"] <= 15.0
