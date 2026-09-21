"""
Domain models and dataclasses for mechanics-agent-skills.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Author:
    """Author of a scientific publication."""
    name: str
    orcid: Optional[str] = None
    affiliations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "orcid": self.orcid,
            "affiliations": self.affiliations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | str) -> "Author":
        if isinstance(data, str):
            return cls(name=data.strip())
        return cls(
            name=data.get("name", "").strip(),
            orcid=data.get("orcid"),
            affiliations=data.get("affiliations", []),
        )


@dataclass
class CitationEdge:
    """Directed citation edge between two works (canonical: citing -> cited)."""
    citing_id: str
    cited_id: str
    provider: str = "openalex"
    retrieved_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citing_id": self.citing_id,
            "cited_id": self.cited_id,
            "provider": self.provider,
            "retrieved_at": self.retrieved_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CitationEdge":
        return cls(
            citing_id=str(data.get("citing_id", "")),
            cited_id=str(data.get("cited_id", "")),
            provider=str(data.get("provider", "openalex")),
            retrieved_at=data.get("retrieved_at"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class OAResult:
    """Open Access resolution result for a work."""
    doi: str
    is_oa: bool = False
    pdf_url: Optional[str] = None
    oa_status: Optional[str] = None
    host_type: Optional[str] = None
    title: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doi": self.doi,
            "is_oa": self.is_oa,
            "pdf_url": self.pdf_url,
            "oa_status": self.oa_status,
            "host_type": self.host_type,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAResult":
        return cls(
            doi=str(data.get("doi", "")),
            is_oa=bool(data.get("is_oa", False)),
            pdf_url=data.get("pdf_url"),
            oa_status=data.get("oa_status"),
            host_type=data.get("host_type"),
            title=data.get("title", ""),
        )

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


@dataclass
class PaperRecord:
    """Canonical scientific literature record."""
    title: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    citations: int = 0
    abstract: str = ""
    sources: List[str] = field(default_factory=list)
    url: Optional[str] = None
    oa_url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "title": self.title,
            "doi": self.doi or "",
            "arxiv_id": self.arxiv_id or "",
            "authors": list(self.authors),
            "year": self.year,
            "journal": self.journal or "",
            "citations": self.citations,
            # Legacy alias compatibility:
            "citation_count": self.citations,
            "abstract": self.abstract,
            "sources": list(self.sources),
            "source": self.sources[0] if self.sources else "",
            "url": self.url or "",
            "oa_url": self.oa_url or "",
        }
        if "openalex_id" in self.extra:
            d["openalex_id"] = self.extra["openalex_id"]
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperRecord":
        title = data.get("title", "").strip()
        doi = data.get("doi") or None
        arxiv_id = data.get("arxiv_id") or None
        raw_authors = data.get("authors", [])
        authors: List[str] = []
        for a in raw_authors:
            if isinstance(a, dict):
                authors.append(a.get("name", "").strip())
            else:
                authors.append(str(a).strip())

        year = data.get("year")
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        journal = data.get("journal") or None
        citations = data.get("citations", data.get("citation_count", 0))
        try:
            citations = int(citations)
        except (ValueError, TypeError):
            citations = 0

        abstract = data.get("abstract", "").strip()

        sources = data.get("sources", [])
        if not sources and data.get("source"):
            sources = [data["source"]]

        url = data.get("url") or None
        oa_url = data.get("oa_url") or None

        extra = dict(data.get("extra", {}))
        if "openalex_id" in data:
            extra["openalex_id"] = data["openalex_id"]

        return cls(
            title=title,
            doi=doi,
            arxiv_id=arxiv_id,
            authors=authors,
            year=year,
            journal=journal,
            citations=citations,
            abstract=abstract,
            sources=sources,
            url=url,
            oa_url=oa_url,
            extra=extra,
        )

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

@dataclass
class EvidenceCard:
    """
    Structured extraction card capturing a verified mechanics fact,
    formula candidate, constitutive parameter, or benchmark table.
    """
    id: str
    element_type: str  # "constitutive", "geometry", "potential", "formula", "benchmark"
    page_number: Optional[int] = None
    verbatim_excerpt: str = ""
    extracted_parameters: Dict[str, Any] = field(default_factory=dict)
    document_title: str = ""
    doi: Optional[str] = None
    confidence: float = 1.0
    source_type: str = "pdf"  # "pdf", "abstract", "text"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "page_number": self.page_number,
            "verbatim_excerpt": self.verbatim_excerpt,
            "extracted_parameters": self.extracted_parameters,
            "document_title": self.document_title,
            "doi": self.doi,
            "confidence": self.confidence,
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceCard":
        return cls(
            id=str(data.get("id", "")),
            element_type=str(data.get("element_type", "")),
            page_number=data.get("page_number"),
            verbatim_excerpt=str(data.get("verbatim_excerpt", "")),
            extracted_parameters=dict(data.get("extracted_parameters", {})),
            document_title=str(data.get("document_title", "")),
            doi=data.get("doi"),
            confidence=float(data.get("confidence", 1.0)),
            source_type=str(data.get("source_type", "pdf")),
        )

