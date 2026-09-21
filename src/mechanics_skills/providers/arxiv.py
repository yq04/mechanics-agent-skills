"""
arXiv API provider adapter.
Critical fixes:
- Strict HTTPS endpoint (https://export.arxiv.org/api/query)
- User-Agent and Accept: */* headers to avoid HTTP 406 Not Acceptable errors
- Proper separation of arXiv IDs and DOIs (never stuffing arXiv URL into DOI field)
- XML parsing using stdlib xml.etree.ElementTree
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, List, Optional

from mechanics_skills.identifiers import extract_arxiv_id, normalize_doi
from mechanics_skills.models import PaperRecord
from mechanics_skills.providers.base import BaseProvider, clean_text

logger = logging.getLogger("mechanics_skills.providers.arxiv")

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArXivProvider(BaseProvider):
    """Adapter for arXiv API with 406 mitigation and clean parsing."""

    name: str = "arxiv"
    BASE_URL = "https://export.arxiv.org/api/query"

    def search(self, query: str, limit: int = 10) -> List[PaperRecord]:
        """Search arXiv preprints."""
        params = {
            "search_query": f"all:{query}",
            "start": "0",
            "max_results": str(limit),
        }
        # CRITICAL FIX: curl User-Agent and Accept: */* to avoid 406 Not Acceptable
        headers = {
            "User-Agent": "curl/8.4.0",
            "Accept": "*/*",
        }

        try:
            resp = self.client.get(self.BASE_URL, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"arXiv returned HTTP {resp.status_code} for query '{query}'")
                return []
            return self.parse_feed(resp.text)
        except Exception as e:
            logger.warning(f"arXiv search error for query '{query}': {e}")
            return []

    def parse_feed(self, xml_content: str) -> List[PaperRecord]:
        """Parse arXiv Atom XML feed."""
        records: List[PaperRecord] = []
        if not xml_content or not xml_content.strip():
            return records

        try:
            root = ET.fromstring(xml_content)
        except Exception as e:
            logger.warning(f"Failed to parse arXiv XML: {e}")
            return records

        for entry in root.findall("atom:entry", ATOM_NS):
            title_elem = entry.find("atom:title", ATOM_NS)
            title = clean_text(title_elem.text if title_elem is not None else "")
            if not title:
                continue

            summary_elem = entry.find("atom:summary", ATOM_NS)
            summary = clean_text(summary_elem.text if summary_elem is not None else "")

            authors: List[str] = []
            for a in entry.findall("atom:author", ATOM_NS):
                name_elem = a.find("atom:name", ATOM_NS)
                if name_elem is not None and name_elem.text:
                    name = clean_text(name_elem.text)
                    if name:
                        authors.append(name)

            id_elem = entry.find("atom:id", ATOM_NS)
            id_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
            arxiv_id = extract_arxiv_id(id_url)

            published_elem = entry.find("atom:published", ATOM_NS)
            published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
            year: Optional[int] = None
            if published and len(published) >= 4:
                try:
                    year = int(published[:4])
                except ValueError:
                    year = None

            # DOI extraction: check <arxiv:doi> or <atom:doi>
            doi_elem = entry.find("arxiv:doi", ATOM_NS)
            if doi_elem is None:
                doi_elem = entry.find("{http://arxiv.org/schemas/atom}doi")
            if doi_elem is None:
                doi_elem = entry.find("atom:doi", ATOM_NS)

            raw_doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None
            doi = normalize_doi(raw_doi) if raw_doi else None

            # Find PDF link or fallback to abs link
            pdf_url = ""
            for link in entry.findall("atom:link", ATOM_NS):
                if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                    pdf_url = link.get("href", "")
                    break
            if not pdf_url and id_url:
                pdf_url = id_url.replace("/abs/", "/pdf/") + ".pdf"

            records.append(
                PaperRecord(
                    title=title,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    authors=authors,
                    year=year,
                    journal="arXiv preprint",
                    citations=0,
                    abstract=summary,
                    sources=["arxiv"],
                    url=id_url,
                    oa_url=pdf_url or id_url,
                    extra={"arxiv_url": id_url},
                )
            )

        return records

