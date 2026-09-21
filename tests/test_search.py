"""
Unit tests for mechanics literature search and query taxonomy expansion.
"""

import pytest
from unittest.mock import MagicMock

from mechanics_skills.models import PaperRecord
from mechanics_skills.search import (
    expand_mechanics_query,
    search_literature,
    MECHANICS_TAXONOMY,
)


def test_taxonomy_structure():
    """Verify that universal solid mechanics taxonomy contains essential categories."""
    assert "constitutive" in MECHANICS_TAXONOMY
    assert "geometry" in MECHANICS_TAXONOMY
    assert "method" in MECHANICS_TAXONOMY
    assert "fields" in MECHANICS_TAXONOMY

    # Check key concepts
    assert "transversely_isotropic" in MECHANICS_TAXONOMY["constitutive"]
    assert "penny_shaped_crack" in MECHANICS_TAXONOMY["geometry"]
    assert "potential_theory" in MECHANICS_TAXONOMY["method"]
    assert "stress_intensity_factor" in MECHANICS_TAXONOMY["fields"]


def test_expand_mechanics_query_empty():
    """Empty or blank queries should return an empty list."""
    assert expand_mechanics_query("") == []
    assert expand_mechanics_query("   ") == []


def test_expand_mechanics_query_basic():
    """Original query must be preserved first, followed by synonyms."""
    base = "penny-shaped crack interaction"
    expanded = expand_mechanics_query(base)
    assert len(expanded) > 1
    assert expanded[0] == base
    # Check that synonyms or terms are included
    lower_exp = [q.lower() for q in expanded]
    assert any("circular crack" in q or "3d disk crack" in q for q in lower_exp)


def test_expand_mechanics_query_abbreviations():
    """Common solid mechanics acronyms (TI, SIF, COD) should be expanded."""
    expanded = expand_mechanics_query("TI crack SIF analysis")
    lower_exp = [q.lower() for q in expanded]
    assert any("transversely isotropic" in q for q in lower_exp)
    assert any("stress intensity factor" in q for q in lower_exp)


def test_expand_mechanics_query_domain_filter():
    """Domain filters should restrict expansions to specified categories."""
    q = "crack in elastic medium"
    expanded_geom = expand_mechanics_query(q, domain_filters=["geometry"])
    expanded_const = expand_mechanics_query(q, domain_filters=["constitutive"])

    # Geometry expansions should differ from constitutive expansions
    assert expanded_geom != expanded_const


def test_search_literature_deduplication_and_filtering(monkeypatch):
    """Test literature search deduplication, source tracking, and year filtering."""
    # Mock providers
    rec1 = PaperRecord(
        title="Exact analysis of penny-shaped cracks",
        doi="10.1016/sample.1",
        year=2015,
        citations=45,
        sources=["crossref"]
    )
    rec2_dup = PaperRecord(
        title="Exact Analysis of Penny-Shaped Cracks",  # Duplicate title
        doi="10.1016/sample.1",
        year=2015,
        citations=50,
        sources=["openalex"]
    )
    rec3_old = PaperRecord(
        title="Historical crack paper",
        doi="10.1098/sample.old",
        year=1965,
        citations=120,
        sources=["arxiv"]
    )

    class FakeCrossref:
        name = "crossref"
        def __init__(self, client=None): pass
        def search(self, query, limit=10): return [rec1]

    class FakeOpenAlex:
        name = "openalex"
        def __init__(self, client=None): pass
        def search(self, query, limit=10): return [rec2_dup]

    class FakeArXiv:
        name = "arxiv"
        def __init__(self, client=None): pass
        def search(self, query, limit=10): return [rec3_old]

    monkeypatch.setattr("mechanics_skills.search.CrossrefProvider", FakeCrossref)
    monkeypatch.setattr("mechanics_skills.search.OpenAlexProvider", FakeOpenAlex)
    monkeypatch.setattr("mechanics_skills.search.ArXivProvider", FakeArXiv)

    # 1. Search without year filter: should return 2 deduplicated papers
    results = search_literature("penny crack", sources=["crossref", "openalex", "arxiv"], expand=False)
    assert len(results) == 2
    # Check that sources were merged
    rec1_merged = next(r for r in results if r.doi == "10.1016/sample.1")
    assert "crossref" in rec1_merged.sources
    assert "openalex" in rec1_merged.sources
    # Citations should take the max (50 > 45)
    assert rec1_merged.citations == 50

    # 2. Search with year filter (2000 to 2024): excludes the 1965 paper
    filtered = search_literature(
        "penny crack",
        sources=["crossref", "openalex", "arxiv"],
        year_start=2000,
        year_end=2024,
        expand=False
    )
    assert len(filtered) == 1
    assert filtered[0].doi == "10.1016/sample.1"
