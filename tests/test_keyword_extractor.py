"""Tests for the keyword / skill extractor."""


def test_extracts_known_skills(extractor):
    text = "Experienced in Python, Django and PostgreSQL."
    skills = extractor.extract_skills(text)
    assert {"Python", "Django", "PostgreSQL"} <= skills


def test_matching_is_case_insensitive(extractor):
    assert "Python" in extractor.extract_skills("PYTHON developer")
    assert "Python" in extractor.extract_skills("python developer")


def test_word_boundary_prevents_partial_match(extractor):
    # "Java" must not be matched inside "JavaScript".
    skills = extractor.extract_skills("Strong JavaScript skills")
    assert "JavaScript" in skills
    assert "Java" not in skills


def test_no_false_positives_on_empty_text(extractor):
    assert extractor.extract_skills("") == set()


def test_extract_experience_years_picks_max(extractor):
    assert extractor.extract_experience_years("3+ years here, 5 years there") == 5
    assert extractor.extract_experience_years("no numbers about tenure") == 0
    assert extractor.extract_experience_years("2-4 years of experience") == 4


def test_extract_keywords_filters_stopwords(extractor):
    text = "We are looking for a backend engineer to build scalable microservices."
    keywords = extractor.extract_keywords(text, top_n=10)
    assert "the" not in keywords and "for" not in keywords
    assert "backend" in keywords or "scalable" in keywords or "microservices" in keywords


def test_count_keyword_matches(extractor):
    matched = extractor.count_keyword_matches("backend and scalable systems", {"backend", "frontend"})
    assert matched == {"backend"}
