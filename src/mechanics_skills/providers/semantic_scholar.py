"""
Semantic Scholar Graph API provider with graceful fallback.
"""

import logging
from typing import Any, Dict, List, Optional

from mechanics_skills.identifiers import normalize_doi
from mechanics_skills.models import PaperRecord
from mechanics_skills.providers.base import BaseProvider, clean_text

logger = logging.getLogger("mechanics_skills.providers.semantic_scholar")


class SemanticScholarProvider(BaseProvider):
    """Adapter for Semantic Scholar Graph API."""

    name: str = "semantic_scholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def search(self, query: str, limit: int = 10) -> List[PaperRecord]:
        """Search papers on Semantic Scholar."""
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": "title,authors,year,citationCount,abstract,externalIds,openAccessPdf,venue",
        }
        headers = {
            "User-Agent": f"MechanicsSemanticScholarBot/3.0 (+mailto:{self.email})",
        }

        try:
            resp = self.client.get(url, params=params, headers=headers)
            if resp.status_code == 429:
                logger.warning("Semantic Scholar rate limited (429). Falling back gracefully.")
                return []
            if resp.status_code != 200:
                logger.warning(f"Semantic Scholar returned status {resp.status_code} for query: {query}")
                return []

            data = resp.json()
            items = data.get("data", [])
            records: List[PaperRecord] = []
            for it in items:
                rec = self._parse_item(it)
                if rec:
                    records.append(rec)
            return records
        except Exception as e:
            logger.warning(f"Semantic Scholar search error: {e}")
            return []

    def get_paper(self, paper_id_or_doi: str) -> Optional[PaperRecord]:
        """Fetch paper metadata by DOI or Semantic Scholar ID."""
        clean_d = normalize_doi(paper_id_or_doi)
        target_id = f"DOI:{clean_d}" if (clean_d and clean_d.startswith("10.")) else paper_id_or_doi
        url = f"{self.BASE_URL}/paper/{target_id}"
        params = {
            "fields": "title,authors,year,citationCount,abstract,externalIds,openAccessPdf,venue"
        }
        headers = {
            "User-Agent": f"MechanicsSemanticScholarBot/3.0 (+mailto:{self.email})",
        }

        try:
            resp = self.client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                return self._parse_item(resp.json())
            return None
        except Exception as e:
            logger.warning(f"Semantic Scholar get_paper error: {e}")
            return None

    def _parse_item(self, it: Dict[str, Any]) -> Optional[PaperRecord]:
        title = clean_text(it.get("title") or "")
        if not title:
            return None

        ext_ids = it.get("externalIds") or {}
        raw_doi = ext_ids.get("DOI")
        doi = normalize_doi(raw_doi)
        arxiv_id = ext_ids.get("ArXiv")

        authors = [
            clean_text(a.get("name", ""))
            for a in it.get("authors", [])
            if a.get("name")
        ]

        year = it.get("year")
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        journal = clean_text(it.get("venue") or "")
        citations = it.get("citationCount", 0)
        abstract = clean_text(it.get("abstract") or "")

        oa_info = it.get("openAccessPdf") or {}
        oa_url = oa_info.get("url") or ""

        url = f"https://doi.org/{doi}" if doi else (f"https://www.semanticscholar.org/paper/{it.get('paperId')}" if it.get("paperId") else "")

        return PaperRecord(
            title=title,
            doi=doi,
            arxiv_id=arxiv_id,
            authors=authors,
            year=year,
            journal=journal,
            citations=citations,
            abstract=abstract,
            sources=["semantic_scholar"],
            url=url,
            oa_url=oa_url,
            extra={"s2_paper_id": it.get("paperId")},
        )

