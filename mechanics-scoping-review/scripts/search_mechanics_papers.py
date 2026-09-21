#!/usr/bin/env python3
"""
search_mechanics_papers.py
==========================
Multi-source literature search CLI for Solid Mechanics, Fracture Mechanics, and Elasticity.
Sources: Crossref, OpenAlex, arXiv, and Semantic Scholar.
Refactored for mechanics-agent-skills v3.0.0 (delegating to mechanics_skills core).
"""

import os
import sys
from pathlib import Path

# Ensure src/ is on sys.path
_repo_root = Path(__file__).resolve().parent.parent.parent
_vendor_dir = Path(__file__).resolve().parent / "_vendor"
if _vendor_dir.is_dir() and str(_vendor_dir) not in sys.path:
    sys.path.insert(0, str(_vendor_dir))
_src_dir = _repo_root / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from mechanics_skills.cli import search_all_sources as core_search_all_sources
from mechanics_skills.cli import search_cli
from mechanics_skills.providers.arxiv import ArXivProvider
from mechanics_skills.providers.crossref import CrossrefProvider
from mechanics_skills.providers.openalex import OpenAlexProvider
from mechanics_skills.providers.semantic_scholar import SemanticScholarProvider


def search_crossref(query, limit=15):
    """Legacy compatibility function for Crossref search."""
    prov = CrossrefProvider()
    return [r.to_dict() for r in prov.search(query, limit=limit)]


def search_openalex(query, limit=15):
    """Legacy compatibility function for OpenAlex search."""
    prov = OpenAlexProvider()
    return [r.to_dict() for r in prov.search(query, limit=limit)]


def search_arxiv(query, limit=10):
    """Legacy compatibility function for arXiv search."""
    prov = ArXivProvider()
    return [r.to_dict() for r in prov.search(query, limit=limit)]


def search_all_sources(query, limit_per_source=10, sources=None):
    """Legacy compatibility function returning list of paper dictionaries."""
    records = core_search_all_sources(query, limit_per_source=limit_per_source, sources=sources)
    return [r.to_dict() for r in records]


def main():
    sys.exit(search_cli())


if __name__ == "__main__":
    main()

