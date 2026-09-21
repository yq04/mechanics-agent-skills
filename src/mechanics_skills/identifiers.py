"""
Identifier normalization, extraction, and deduplication helpers.
"""

import re
import difflib
from typing import Any, Optional, Union
from mechanics_skills.models import PaperRecord

DOI_PREFIX_REGEX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
ARXIV_ID_REGEX = re.compile(
    r"(?:arxiv:\s*|https?://arxiv\.org/(?:abs|pdf)/)?([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})",
    re.IGNORECASE,
)
TRAILING_PUNCT = ".,;:>])"


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """
    Normalize DOI:
    - Strips URL schemes (https://doi.org/, http://dx.doi.org/, doi:)
    - Lowercase
    - Strips outer whitespace
    - Strips accidental trailing punctuation (e.g., period, semicolon at end of citation)
    """
    if not doi:
        return None
    s = str(doi).strip()
    s = DOI_PREFIX_REGEX.sub("", s).strip()
    s = s.lower()
    s = s.rstrip(TRAILING_PUNCT).strip()
    if not s or not s.startswith("10."):
        m = re.search(r"(10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+)", s)
        if m:
            s = m.group(1).lower()
            s = s.rstrip(TRAILING_PUNCT).strip()
        else:
            return s if s else None
    return s


def extract_arxiv_id(text: Optional[str]) -> Optional[str]:
    """
    Extract canonical arXiv identifier from text or URL.
    Examples:
        '2101.12345' -> '2101.12345'
        'arXiv:2101.12345v2' -> '2101.12345v2'
        'https://arxiv.org/abs/2101.12345' -> '2101.12345'
        'math.PR/0306123' -> 'math.PR/0306123'
    """
    if not text:
        return None
    s = str(text).strip()
    m = ARXIV_ID_REGEX.search(s)
    if m:
        return m.group(1).lower()
    return None


def clean_title_for_comparison(title: Optional[str]) -> str:
    """Normalize a title string for similarity comparison."""
    if not title:
        return ""
    t = re.sub(r"[^\w\s]", " ", str(title).lower())
    return " ".join(t.split())


def generate_dedup_key(record: Union[PaperRecord, dict]) -> str:
    """
    Generate stable deduplication key for a paper.
    Priority:
    1. Normalized DOI (doi:...)
    2. Normalized arXiv ID (arxiv:...)
    3. Normalized title slug (title:...)
    """
    if isinstance(record, PaperRecord):
        doi = record.doi
        arxiv_id = record.arxiv_id
        title = record.title
    else:
        doi = record.get("doi")
        arxiv_id = record.get("arxiv_id")
        title = record.get("title", "")

    clean_d = normalize_doi(doi)
    if clean_d and clean_d.startswith("10."):
        return f"doi:{clean_d}"

    clean_ar = extract_arxiv_id(arxiv_id)
    if not clean_ar and doi:
        clean_ar = extract_arxiv_id(doi)
    if clean_ar:
        return f"arxiv:{clean_ar}"

    norm_title = clean_title_for_comparison(title)
    if norm_title:
        return f"title:{norm_title}"

    return "unknown:empty"


def fuzzy_title_match(title1: Optional[str], title2: Optional[str], threshold: float = 0.88) -> bool:
    """
    Check if two titles match closely using normalized character sequence ratio.
    """
    t1 = clean_title_for_comparison(title1)
    t2 = clean_title_for_comparison(title2)
    if not t1 or not t2:
        return False
    if t1 == t2:
        return True
    ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
    return ratio >= threshold
