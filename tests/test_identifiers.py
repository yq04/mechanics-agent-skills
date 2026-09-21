"""
Unit tests for mechanics_skills.identifiers module.
"""

from mechanics_skills.identifiers import (
    clean_title_for_comparison,
    extract_arxiv_id,
    fuzzy_title_match,
    generate_dedup_key,
    normalize_doi,
)
from mechanics_skills.models import PaperRecord


def test_normalize_doi():
    # HTTPS resolver
    assert normalize_doi("https://doi.org/10.1016/J.JMPS.2020.104123") == "10.1016/j.jmps.2020.104123"
    # HTTP dx resolver
    assert normalize_doi("http://dx.doi.org/10.1007/s10704-021-00567-8") == "10.1007/s10704-021-00567-8"
    # doi: prefix with spaces
    assert normalize_doi("doi: 10.1098/rspa.2019.0123") == "10.1098/rspa.2019.0123"
    # Trailing punctuation from text scraping
    assert normalize_doi("10.1016/j.jmps.2020.104123.") == "10.1016/j.jmps.2020.104123"
    assert normalize_doi("10.1016/j.jmps.2020.104123;") == "10.1016/j.jmps.2020.104123"
    # Embedded in sentence
    assert normalize_doi("See paper at 10.1016/j.jmps.2020.104123 for details") == "10.1016/j.jmps.2020.104123"
    # Empty / None
    assert normalize_doi(None) is None
    assert normalize_doi("") is None


def test_extract_arxiv_id():
    assert extract_arxiv_id("arXiv:2101.12345") == "2101.12345"
    assert extract_arxiv_id("arxiv:2101.12345v3") == "2101.12345v3"
    assert extract_arxiv_id("https://arxiv.org/abs/2101.12345") == "2101.12345"
    assert extract_arxiv_id("https://arxiv.org/pdf/2101.12345v2.pdf") == "2101.12345v2"
    assert extract_arxiv_id("math.PR/0306123") == "math.pr/0306123"
    assert extract_arxiv_id("Just a random text") is None
    assert extract_arxiv_id(None) is None


def test_generate_dedup_key():
    p1 = PaperRecord(title="Elasticity of Cracks", doi="10.1016/j.jmps.2020.104123")
    assert generate_dedup_key(p1) == "doi:10.1016/j.jmps.2020.104123"

    p2 = PaperRecord(title="Fabrikant Potential Theory", arxiv_id="2101.12345")
    assert generate_dedup_key(p2) == "arxiv:2101.12345"

    p3 = PaperRecord(title="Three-Dimensional Crack Problems in Transversely Isotropic Media")
    assert generate_dedup_key(p3).startswith("title:three dimensional crack problems")


def test_fuzzy_title_match():
    t1 = "Stress intensity factors for penny-shaped cracks in transversely isotropic media"
    t2 = "Stress Intensity Factors for Penny-Shaped Cracks in Transversely Isotropic Media."
    t3 = "Stress intensity factors for penny-shaped cracks in transversely isotropic media: A review"
    t4 = "Fluid mechanics of turbulent boundary layers"

    assert fuzzy_title_match(t1, t2) is True
    assert fuzzy_title_match(t1, t3) is True
    assert fuzzy_title_match(t1, t4) is False
    assert fuzzy_title_match("", "") is False

