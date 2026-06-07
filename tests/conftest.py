"""Shared pytest fixtures."""

import json
from pathlib import Path

import pytest

from extractors.keyword_extractor import KeywordExtractor

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / "data" / "skills_taxonomy.json"
CONFIG_PATH = ROOT / "data" / "config.json"


@pytest.fixture(scope="session")
def taxonomy_path() -> Path:
    return TAXONOMY_PATH


@pytest.fixture(scope="session")
def config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def extractor(taxonomy_path) -> KeywordExtractor:
    return KeywordExtractor(taxonomy_path)
