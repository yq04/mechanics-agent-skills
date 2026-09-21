"""
OpenAlex API provider adhering to 2026 specifications.
Enforces max 100 items per page, polite pool mailto, cursor-based pagination,
and abstract inverted index decoding.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from mechanics_skills.identifiers import normalize_doi
from mechanics_skills.models import PaperRecord
from mechanics_skills.providers.base import BaseProvider, clean_text

logger = logging.getLogger("mechanics_skills.providers.openalex")


def decode_abstract_inverted_index(inv: Optional[Dict[str, List[int]]]) -> str:
    """Reconstruct plain-text abstract from OpenAlex abstract_inverted_index."""
    if not inv or not isinstance(inv, dict):
        return ""
    word_pos = []
    for word, positions in inv.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort(key=lambda x: x[0])
    return clean_text(" ".join([w[1] for w in word_pos]))


class OpenAlexProvider(BaseProvider):
    """Adapter for OpenAlex REST API."""

    name: str = "openalex"
    BASE_URL = "https://api.openalex.org"
    MAX_PER_PAGE = 100  # 2026 OpenAlex spec strictly limits per-page to 100

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send GET request to OpenAlex endpoint with mailto."""
        p = dict(params) if params else {}
        if self.email and "mailto" not in p:
            p["mailto"] = self.email

        url = urljoin(self.BASE_URL, endpoint) if not endpoint.startswith("http") else endpoint
        headers = {
            "User-Agent": f"MechanicsOpenAlexBot/3.0 (+mailto:{self.email})",
        }
        resp = self.client.get(url, params=p, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            logger.warning(f"OpenAlex rate limited: {resp.text[:200]}")
            return {}
        else:
            logger.warning(f"OpenAlex returned {resp.status_code} for {url}")
            return {}

    def parse_work_item(self, it: Dict[str, Any]) -> Optional[PaperRecord]:
        """Convert OpenAlex work object to PaperRecord."""
        raw_doi = it.get("doi") or ""
        doi = normalize_doi(raw_doi)
        title = clean_text(it.get("title") or "")
        if not title:
            return None

        authors = [
            clean_text(a.get("author", {}).get("display_name", ""))
            for a in it.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]

        year = it.get("publication_year")
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        primary_loc = it.get("primary_location") or {}
        source_info = primary_loc.get("source") or {}
        journal = clean_text(source_info.get("display_name") or "")

        citations = it.get("cited_by_count", 0)

        oa_info = it.get("open_access") or {}
        oa_url = oa_info.get("oa_url") or ""

        abstract = decode_abstract_inverted_index(it.get("abstract_inverted_index"))

        work_id = it.get("id", "")
        extra = {"openalex_id": work_id}

        return PaperRecord(
            title=title,
            doi=doi,
            authors=authors,
            year=year,
            journal=journal,
            citations=citations,
            abstract=abstract,
            sources=["openalex"],
            url=raw_doi or (f"https://openalex.org/{work_id}" if work_id else ""),
            oa_url=oa_url,
            extra=extra,
        )

    def search(self, query: str, limit: int = 15) -> List[PaperRecord]:
        """Search works by text query."""
        results: List[PaperRecord] = []
        page_size = min(limit, self.MAX_PER_PAGE)
        params = {
            "search": query,
            "per_page": page_size,
        }
        data = self._make_request("/works", params=params)
        for it in data.get("results", []):
            rec = self.parse_work_item(it)
            if rec:
                results.append(rec)
            if len(results) >= limit:
                break
        return results

    def get_work(self, id_or_doi: str) -> Dict[str, Any]:
        """Get work by OpenAlex ID or DOI."""
        clean_d = normalize_doi(id_or_doi)
        if clean_d and clean_d.startswith("10."):
            endpoint = f"/works/https://doi.org/{clean_d}"
        else:
            clean_id = id_or_doi.split("/")[-1]
            endpoint = f"/works/{clean_id}"
        return self._make_request(endpoint)

    def search_works(
        self,
        search: Optional[str] = None,
        filter_params: Optional[Dict[str, Any]] = None,
        per_page: int = 100,
        page: int = 1,
        sort: Optional[str] = None,
        select: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """OpenAlex works search endpoint with standard pagination."""
        params: Dict[str, Any] = {
            "per-page": min(per_page, self.MAX_PER_PAGE),
            "page": page,
        }
        if search:
            params["search"] = search
        if filter_params:
            filter_str = ",".join([f"{k}:{v}" for k, v in filter_params.items()])
            params["filter"] = filter_str
        if sort:
            params["sort"] = sort
        if select:
            params["select"] = ",".join(select)

        return self._make_request("/works", params)

    def get_entity(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Get a single entity by ID or DOI."""
        if entity_type == "works":
            return self.get_work(entity_id)
        clean_id = entity_id.split("/")[-1]
        endpoint = f"/{entity_type}/{clean_id}"
        return self._make_request(endpoint)

    def batch_lookup(
        self,
        entity_type: str,
        ids: List[str],
        id_field: str = "openalex_id",
    ) -> List[Dict[str, Any]]:
        """Look up multiple entities by batch in chunks of 50."""
        all_results: List[Dict[str, Any]] = []
        for i in range(0, len(ids), 50):
            batch = ids[i : i + 50]
            clean_ids = [bid.split("/")[-1] for bid in batch]
            filter_value = "|".join(clean_ids)
            field_name = "openalex" if id_field == "openalex_id" else id_field
            params = {
                "filter": f"{field_name}:{filter_value}",
                "per-page": 50,
            }
            resp = self._make_request(f"/{entity_type}", params)
            all_results.extend(resp.get("results", []))
        return all_results

    def paginate_all(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
        use_cursor: bool = False,
    ) -> List[Dict[str, Any]]:
        """Paginate through all results, optionally using cursor-based pagination."""
        p = dict(params) if params else {}
        p["per-page"] = self.MAX_PER_PAGE
        all_results: List[Dict[str, Any]] = []

        if use_cursor:
            p["cursor"] = "*"
            while True:
                resp = self._make_request(endpoint, p)
                results = resp.get("results", [])
                if not results:
                    break
                all_results.extend(results)
                if max_results and len(all_results) >= max_results:
                    return all_results[:max_results]
                next_cursor = resp.get("meta", {}).get("next_cursor")
                if not next_cursor:
                    break
                p["cursor"] = next_cursor
            return all_results

        p["page"] = 1
        while True:
            resp = self._make_request(endpoint, p)
            results = resp.get("results", [])
            if not results:
                break
            all_results.extend(results)
            if max_results and len(all_results) >= max_results:
                return all_results[:max_results]
            meta = resp.get("meta", {})
            total_count = meta.get("count", 0)
            if len(all_results) >= total_count:
                break
            p["page"] += 1
            if p["page"] > 100:  # OpenAlex basic pagination cap is 10k items (100 pages of 100)
                break

        return all_results

    def sample_works(
        self,
        sample_size: int,
        seed: Optional[int] = None,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get random sample of works."""
        params: Dict[str, Any] = {
            "sample": min(sample_size, 10000),
            "per-page": self.MAX_PER_PAGE,
        }
        if seed is not None:
            params["seed"] = seed
        if filter_params:
            filter_str = ",".join([f"{k}:{v}" for k, v in filter_params.items()])
            params["filter"] = filter_str

        resp = self._make_request("/works", params)
        return resp.get("results", [])

    def group_by(
        self,
        entity_type: str,
        group_field: str,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate results by field."""
        params: Dict[str, Any] = {"group_by": group_field}
        if filter_params:
            filter_str = ",".join([f"{k}:{v}" for k, v in filter_params.items()])
            params["filter"] = filter_str
        resp = self._make_request(f"/{entity_type}", params)
        return resp.get("group_by", [])

