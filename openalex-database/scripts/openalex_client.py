#!/usr/bin/env python3
"""
OpenAlex API Client with rate limiting and error handling.
Refactored for mechanics-agent-skills v3.0.0.

Provides a robust client for interacting with the OpenAlex API with:
- Zero external dependencies required (uses mechanics_skills.http or urllib)
- Automatic rate limiting (polite pool: 10 req/sec)
- Exponential backoff retry logic
- Modern OpenAlex 2026 pagination & cursor support
- Batch operations support
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

# Ensure src/ is on sys.path for backward compatibility when running without pip install
_repo_root = Path(__file__).resolve().parent.parent.parent
_vendor_dir = Path(__file__).resolve().parent / "_vendor"
if _vendor_dir.is_dir() and str(_vendor_dir) not in sys.path:
    sys.path.insert(0, str(_vendor_dir))
_src_dir = _repo_root / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from mechanics_skills.config import DEFAULT_EMAIL
from mechanics_skills.http import HTTPClient
from mechanics_skills.providers.openalex import OpenAlexProvider


class OpenAlexClient:
    """Client for OpenAlex API with rate limiting and error handling."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: Optional[str] = None, requests_per_second: int = 10):
        """
        Initialize OpenAlex client.

        Args:
            email: Email for polite pool (10x rate limit boost)
            requests_per_second: Max requests per second (default: 10 for polite pool)
        """
        self.email = email or DEFAULT_EMAIL
        self.requests_per_second = requests_per_second
        self.min_delay = 1.0 / requests_per_second
        self.last_request_time = 0.0

        # Initialize underlying mechanics_skills provider & http client
        self._http = HTTPClient()
        self._provider = OpenAlexProvider(client=self._http, email=self.email)

    def _rate_limit(self) -> None:
        """Ensure requests don't exceed rate limit."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        self.last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
    ) -> Dict[str, Any]:
        """
        Make API request with retry logic. Zero-dependency implementation.

        Args:
            endpoint: API endpoint (e.g., '/works', '/authors')
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            JSON response as dictionary
        """
        if params is None:
            params = {}

        p = dict(params)
        if self.email and "mailto" not in p:
            p["mailto"] = self.email

        url = urljoin(self.BASE_URL, endpoint) if not endpoint.startswith("http") else endpoint
        headers = {
            "User-Agent": f"MechanicsOpenAlexBot/3.0 (+mailto:{self.email})",
        }

        for attempt in range(max_retries):
            try:
                self._rate_limit()
                resp = self._http.get(url, params=p, headers=headers, timeout=30, max_retries=1)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code in (403, 429):
                    wait_time = 2 ** attempt
                    print(f"Rate limited (status {resp.status_code}). Waiting {wait_time}s before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                elif resp.status_code >= 500:
                    wait_time = 2 ** attempt
                    print(f"Server error (status {resp.status_code}). Waiting {wait_time}s before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                else:
                    return resp.json() if resp.text else {}

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Request error: {e}. Waiting {wait_time}s before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed after {max_retries} retries: {e}") from e

        raise Exception(f"Failed after {max_retries} retries")

    def search_works(
        self,
        search: Optional[str] = None,
        filter_params: Optional[Dict[str, Any]] = None,
        per_page: int = 100,
        page: int = 1,
        sort: Optional[str] = None,
        select: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search works with filters (caps per_page to 100 per 2026 specs)."""
        # OpenAlex 2026 specification strictly enforces max 100 items per page
        safe_per_page = min(per_page, 100)
        return self._provider.search_works(
            search=search,
            filter_params=filter_params,
            per_page=safe_per_page,
            page=page,
            sort=sort,
            select=select,
        )

    def get_entity(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Get single entity by ID or external identifier."""
        return self._provider.get_entity(entity_type, entity_id)

    def batch_lookup(
        self,
        entity_type: str,
        ids: List[str],
        id_field: str = "openalex_id",
    ) -> List[Dict[str, Any]]:
        """Look up multiple entities by ID efficiently."""
        return self._provider.batch_lookup(entity_type, ids, id_field=id_field)

    def paginate_all(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Paginate through all results safely."""
        return self._provider.paginate_all(endpoint, params=params, max_results=max_results)

    def sample_works(
        self,
        sample_size: int,
        seed: Optional[int] = None,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get random sample of works."""
        return self._provider.sample_works(sample_size, seed=seed, filter_params=filter_params)

    def group_by(
        self,
        entity_type: str,
        group_field: str,
        filter_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate results by field."""
        return self._provider.group_by(entity_type, group_field, filter_params=filter_params)


if __name__ == "__main__":
    # Example usage
    client = OpenAlexClient(email="your-email@example.com")

    results = client.search_works(
        search="machine learning",
        filter_params={"publication_year": "2023"},
        per_page=10,
    )

    print(f"Found {results.get('meta', {}).get('count', 0)} works")
    for work in results.get("results", []):
        print(f"- {work.get('title')}")

