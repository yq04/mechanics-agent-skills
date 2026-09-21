"""
Unpaywall Open Access API provider.
"""

import logging
from typing import Any, Dict, Optional

from mechanics_skills.identifiers import normalize_doi
from mechanics_skills.models import OAResult, PaperRecord
from mechanics_skills.providers.base import BaseProvider, clean_text

logger = logging.getLogger("mechanics_skills.providers.unpaywall")


class UnpaywallProvider(BaseProvider):
    """Adapter for Unpaywall v2 API."""

    name: str = "unpaywall"
    BASE_URL = "https://api.unpaywall.org/v2"

    def search(self, query: str, limit: int = 15) -> list[PaperRecord]:
        """Unpaywall does not offer full-text search; raises NotImplementedError."""
        raise NotImplementedError("Unpaywall API only supports single DOI lookup via find_oa().")

    def find_oa(self, doi: str) -> OAResult:
        """Query Unpaywall for Open Access PDF link and metadata."""
        clean_d = normalize_doi(doi)
        if not clean_d:
            return OAResult(doi=doi, is_oa=False)

        url = f"{self.BASE_URL}/{clean_d}"
        email = self.email or "unpaywall_client@example.org"
        params = {"email": email}
        headers = {"User-Agent": f"MechanicsAgentSkills/3.1.0 (mailto:{email})"}

        try:
            resp = self.client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.info(f"Unpaywall returned {resp.status_code} for {clean_d}")
                return OAResult(doi=clean_d, is_oa=False)

            data = resp.json()
            is_oa = bool(data.get("is_oa", False))
            oa_status = data.get("oa_status")
            title = clean_text(data.get("title") or "")

            best_loc = data.get("best_oa_location") or {}
            pdf_url = best_loc.get("url_for_pdf") or best_loc.get("url")
            host_type = best_loc.get("host_type")

            return OAResult(
                doi=clean_d,
                is_oa=is_oa,
                pdf_url=pdf_url,
                oa_status=oa_status,
                host_type=host_type,
                title=title,
            )
        except Exception as e:
            logger.warning(f"Unpaywall lookup error for {doi}: {e}")
            return OAResult(doi=clean_d, is_oa=False)

