"""
Academic provider adapters for Crossref, OpenAlex, arXiv, Unpaywall, and Semantic Scholar.
"""

from mechanics_skills.providers.base import BaseProvider, clean_text
from mechanics_skills.providers.crossref import CrossrefProvider
from mechanics_skills.providers.openalex import OpenAlexProvider
from mechanics_skills.providers.arxiv import ArXivProvider
from mechanics_skills.providers.unpaywall import UnpaywallProvider
from mechanics_skills.providers.semantic_scholar import SemanticScholarProvider

__all__ = [
    "BaseProvider",
    "clean_text",
    "CrossrefProvider",
    "OpenAlexProvider",
    "ArXivProvider",
    "UnpaywallProvider",
    "SemanticScholarProvider",
]

