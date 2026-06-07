"""Tests for the job-description parser."""

from parsers.jd_parser import JDParser, JDRequirements

SAMPLE_JD = """Senior Python Developer

Required Skills:
- Python
- Django
- SQL

Preferred Skills:
- Docker
- AWS

Experience:
- 3+ years of professional Python development
"""


def test_parse_returns_requirements(extractor):
    jd = JDParser(extractor).parse(SAMPLE_JD)
    assert isinstance(jd, JDRequirements)


def test_required_and_preferred_are_separated(extractor):
    jd = JDParser(extractor).parse(SAMPLE_JD)
    assert {"Python", "Django", "SQL"} <= jd.required_skills
    assert {"Docker", "AWS"} <= jd.preferred_skills
    # A required skill must never also be preferred.
    assert jd.required_skills.isdisjoint(jd.preferred_skills)


def test_minimum_experience_detected(extractor):
    jd = JDParser(extractor).parse(SAMPLE_JD)
    assert jd.min_years == 3


def test_unstructured_jd_still_finds_required_skills(extractor):
    """A free-form JD with no headings should fall back to scanning everything."""
    jd = JDParser(extractor).parse("We need someone strong in Python and SQL.")
    assert {"Python", "SQL"} <= jd.required_skills


def test_keywords_are_populated(extractor):
    jd = JDParser(extractor).parse(SAMPLE_JD)
    assert len(jd.keywords) > 0
