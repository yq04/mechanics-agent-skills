"""
Crossref REST API provider.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from mechanics_skills.identifiers import normalize_doi
from mechanics_skills.models import PaperRecord
from mechanics_skills.providers.base import BaseProvider, clean_text

logger = logging.getLogger("mechanics_skills.providers.crossref")


class CrossrefProvider(BaseProvider):
    """Adapter for Crossref Works API."""

    name: str = "crossref"
    BASE_URL = "https://api.crossref.org/works"

    def search(self, query: str, limit: int = 15) -> List[PaperRecord]:
        params = {
            "query": query,
            "rows": limit,
            "mailto": self.email,
        }
        headers = {
            "User-Agent": f"MechanicsCrossrefBot/3.0 (+mailto:{self.email})",
        }
        try:
            resp = self.client.get(self.BASE_URL, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Crossref returned status {resp.status_code} for query: {query}")
                return []
            data = resp.json()
            items = data.get("message", {}).get("items", [])
            records: List[PaperRecord] = []
            for it in items:
                rec = self._parse_item(it)
                if rec:
                    records.append(rec)
            return records
        except Exception as e:
            logger.warning(f"Crossref search error: {e}")
            return []

    def get_work(self, doi: str) -> Optional[PaperRecord]:
        clean_d = normalize_doi(doi)
        if not clean_d:
            return None
        url = f"{self.BASE_URL}/{clean_d}"
        params = {"mailto": self.email}
        headers = {"User-Agent": f"MechanicsCrossrefBot/3.0 (+mailto:{self.email})"}
        try:
            resp = self.client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                item = data.get("message", {})
                return self._parse_item(item)
            return None
        except Exception as e:
            logger.warning(f"Crossref get_work error for {doi}: {e}")
            return None

    def _parse_item(self, it: Dict[str, Any]) -> Optional[PaperRecord]:
        raw_doi = it.get("DOI", "")
        doi = normalize_doi(raw_doi)
        title_list = it.get("title") or [""]
        title = clean_text(title_list[0] if title_list else "")
        if not title:
            return None

        authors: List[str] = []
        for a in it.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            name = clean_text(f"{given} {family}")
            if name:
                authors.append(name)

        year: Optional[int] = None
        for date_key in ("published-print", "published-online", "issued", "created"):
            date_dict = it.get(date_key)
            if date_dict and "date-parts" in date_dict and date_dict["date-parts"]:
                parts = date_dict["date-parts"][0]
                if parts and isinstance(parts[0], int):
                    year = parts[0]
                    break

        container = it.get("container-title") or [""]
        journal = clean_text(container[0] if container else "")

        citations = it.get("is-referenced-by-count", 0)

        raw_abstract = it.get("abstract", "")
        clean_abstract = clean_text(re.sub(r"<[^>]+>", "", raw_abstract))

        url = it.get("URL") or (f"https://doi.org/{doi}" if doi else "")

        return PaperRecord(
            title=title,
            doi=doi,
            authors=authors,
            year=year,
            journal=journal,
            citations=citations,
            abstract=clean_abstract,
            sources=["crossref"],
            url=url,
        )

