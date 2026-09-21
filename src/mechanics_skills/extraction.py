"""
PDF and Full-Text Evidence & Formula Extraction Engine for Solid Mechanics.
"""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from mechanics_skills.models import EvidenceCard


def _generate_evidence_id(
    title: str,
    page: Optional[int],
    element_type: str,
    excerpt: str,
    source_type: str = "pdf",
) -> str:
    """Generate a stable deterministic ID for an evidence card."""
    page_tag = "ABS" if (source_type == "abstract" or page is None) else str(page)
    seed = f"{title}_{source_type}_{page_tag}_{element_type}_{excerpt[:50]}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    return f"EV_{element_type[:3].upper()}_{page_tag}_{h}"


def extract_pages_from_pdf(
    pdf_source: Union[str, Path, bytes]
) -> List[Tuple[int, str]]:
    """
    Extract page-mapped text from a PDF file using PyMuPDF (fitz) if available.
    Returns list of (page_number_1_based, text).
    """
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            fitz = None

    if fitz is None:
        if isinstance(pdf_source, (str, Path)) and not str(pdf_source).endswith(".pdf"):
            try:
                with open(pdf_source, "r", encoding="utf-8", errors="ignore") as f:
                    return [(1, f.read())]
            except Exception:
                pass
        raise ImportError(
            "PyMuPDF is not installed. Install with 'pip install pymupdf' to parse PDF files."
        )

    pages: List[Tuple[int, str]] = []
    if isinstance(pdf_source, bytes):
        doc = fitz.open(stream=pdf_source, filetype="pdf")
    else:
        doc = fitz.open(str(pdf_source))

    try:
        for pno in range(len(doc)):
            page = doc[pno]
            text = page.get_text("text") or ""
            pages.append((pno + 1, text))
    finally:
        doc.close()

    return pages


# Regex patterns for mechanics elements
RE_CONSTITUTIVE_STIFFNESS = re.compile(
    r"\b(c(?:_\{?\d{2}\}?|\d{2}))\s*=\s*([0-9\.\+\-eE]+)\s*(?:GPa|MPa|N/m\^?2|10\^?\d+\s*N/m\^?2)?",
    re.IGNORECASE,
)
RE_ELASTIC_MODULUS = re.compile(
    r"\b([EG\u03bd\u03bc](?:_\{?[0-9]+\}?|[0-9]+)?)\s*=\s*([0-9\.\+\-eE]+)\s*(GPa|MPa|N/m\^?2)?",
    re.IGNORECASE,
)
RE_POISSON = re.compile(
    r"(?:poisson(?:'s)?\s*ratio|\bnu(?:_\{?[0-9]+\}?|[0-9]+)?\b|\b\u03bd(?:_\{?[0-9]+\}?|[0-9]+)?\b)\s*=\s*([0-9\.]+)",
    re.IGNORECASE,
)
RE_TI_MATERIAL = re.compile(
    r"\b(transversely isotropic|transverse isotropy|hexagonal|piezoelectric|orthotropic|anisotropic)\b",
    re.IGNORECASE,
)

RE_CRACK_GEOM = re.compile(
    r"\b(penny-shaped crack|circular crack|elliptical crack|coplanar cracks|parallel cracks|interface crack|inclusion)\b",
    re.IGNORECASE,
)
RE_CRACK_RADIUS = re.compile(
    r"(?:radius|semi-axis)\s*(?:a|R)\s*=\s*([0-9\.\+\-eE]+)\s*(?:mm|m|cm|\u03bcm)?",
    re.IGNORECASE,
)
RE_SPACING = re.compile(
    r"(?:distance|spacing|offset)\s*(?:h|d|l)\s*=\s*([0-9\.\+\-eE]+)",
    re.IGNORECASE,
)
RE_BC_TRACTION = re.compile(
    r"\b(traction-free|uniform tension|internal pressure|shear loading|normal pressure)\b",
    re.IGNORECASE,
)

RE_POTENTIALS = re.compile(
    r"\b(Fabrikant(?:'s)?\s*(?:potential|representation|method)|Papkovich-Neuber|Muskhelishvili|Stroh formalism|Boussinesq|Hankel transform|dual integral equation)\b",
    re.IGNORECASE,
)

RE_SIF_FORMULA = re.compile(
    r"(K_?[I|II|III|1|2|3]\s*=\s*[^;\n]{5,100})",
    re.IGNORECASE,
)
RE_COD_FORMULA = re.compile(
    r"((?:w\(r\)|COD|\u0394\s*u_?z|u_?z)\s*=\s*[^;\n]{5,100})",
    re.IGNORECASE,
)
RE_ERR_FORMULA = re.compile(
    r"(\b(?:G|J)\s*=\s*[^;\n]{5,80})",
    re.IGNORECASE,
)

RE_TABLE_BENCHMARK = re.compile(
    r"(Table\s+\d+[\s\:\.\-]+[^\n]{5,120})",
    re.IGNORECASE,
)
RE_BENCHMARK_KEYWORDS = re.compile(
    r"\b(stress intensity factor ratio|interaction factor|Collins|benchmark|normalized SIF|K_I\s*/\s*K_0)\b",
    re.IGNORECASE,
)


def extract_evidence_from_text(
    text: str,
    document_title: str = "",
    doi: Optional[str] = None,
    page_number: Optional[int] = 1,
    source_type: str = "text",
) -> List[EvidenceCard]:
    """
    Extract mechanics evidence cards from a block of text on a given page.
    Scans for constitutive relations, defect geometries, potentials, formulas, and benchmarks.
    When source_type == 'abstract', page_number is explicitly None.
    """
    actual_page: Optional[int] = None if source_type == "abstract" else page_number
    cards: List[EvidenceCard] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 20]

    for para in paragraphs:
        # 1. Constitutive properties
        stiffness_matches = RE_CONSTITUTIVE_STIFFNESS.findall(para)
        modulus_matches = RE_ELASTIC_MODULUS.findall(para)
        ti_matches = RE_TI_MATERIAL.findall(para)
        poisson_matches = RE_POISSON.findall(para)

        if stiffness_matches or modulus_matches or ti_matches or poisson_matches:
            params: Dict[str, Any] = {}
            if ti_matches:
                params["symmetry"] = list(set(ti_matches))
            if stiffness_matches:
                params["stiffness_constants"] = {m[0]: m[1] for m in stiffness_matches}
            if modulus_matches:
                params["elastic_moduli"] = {m[0]: m[1] for m in modulus_matches}
            if poisson_matches:
                params["poisson_ratio"] = poisson_matches[0]

            cards.append(
                EvidenceCard(
                    id=_generate_evidence_id(document_title, actual_page, "constitutive", para),
                    element_type="constitutive",
                    page_number=actual_page,
                    source_type=source_type,
                    verbatim_excerpt=para[:300],
                    extracted_parameters=params,
                    document_title=document_title,
                    doi=doi,
                    confidence=0.95 if stiffness_matches else 0.8,
                )
            )

        # 2. Defect geometry & boundary conditions
        geom_matches = RE_CRACK_GEOM.findall(para)
        bc_matches = RE_BC_TRACTION.findall(para)
        radius_matches = RE_CRACK_RADIUS.findall(para)
        spacing_matches = RE_SPACING.findall(para)

        if geom_matches or (bc_matches and ("crack" in para.lower() or "defect" in para.lower())):
            params = {}
            if geom_matches:
                params["defect_type"] = list(set(geom_matches))
            if bc_matches:
                params["boundary_condition"] = list(set(bc_matches))
            if radius_matches:
                params["dimensions"] = {"radius_or_axis": radius_matches[0]}
            if spacing_matches:
                params["spacing"] = spacing_matches[0]

            cards.append(
                EvidenceCard(
                    id=_generate_evidence_id(document_title, actual_page, "geometry", para),
                    element_type="geometry",
                    page_number=actual_page,
                    source_type=source_type,
                    verbatim_excerpt=para[:300],
                    extracted_parameters=params,
                    document_title=document_title,
                    doi=doi,
                    confidence=0.9,
                )
            )

        # 3. Analytical potentials
        potential_matches = RE_POTENTIALS.findall(para)
        if potential_matches:
            cards.append(
                EvidenceCard(
                    id=_generate_evidence_id(document_title, actual_page, "potential", para),
                    element_type="potential",
                    page_number=actual_page,
                    source_type=source_type,
                    verbatim_excerpt=para[:300],
                    extracted_parameters={"representations": list(set(potential_matches))},
                    document_title=document_title,
                    doi=doi,
                    confidence=0.95,
                )
            )

        # 4. Formula candidates (SIF, COD, Energy Release Rate)
        sif_matches = RE_SIF_FORMULA.findall(para)
        cod_matches = RE_COD_FORMULA.findall(para)
        err_matches = RE_ERR_FORMULA.findall(para)

        if sif_matches or cod_matches or err_matches:
            formula_dict: Dict[str, List[str]] = {}
            if sif_matches:
                formula_dict["SIF"] = [m.strip() for m in sif_matches[:3]]
            if cod_matches:
                formula_dict["COD"] = [m.strip() for m in cod_matches[:3]]
            if err_matches:
                formula_dict["ERR_J"] = [m.strip() for m in err_matches[:3]]

            cards.append(
                EvidenceCard(
                    id=_generate_evidence_id(document_title, actual_page, "formula", para),
                    element_type="formula",
                    page_number=actual_page,
                    source_type=source_type,
                    verbatim_excerpt=para[:350],
                    extracted_parameters={"formula_candidates": formula_dict},
                    document_title=document_title,
                    doi=doi,
                    confidence=0.85,
                )
            )

        # 5. Benchmark tables & figures
        table_matches = RE_TABLE_BENCHMARK.findall(para)
        if table_matches and RE_BENCHMARK_KEYWORDS.search(para):
            cards.append(
                EvidenceCard(
                    id=_generate_evidence_id(document_title, actual_page, "benchmark", para),
                    element_type="benchmark",
                    page_number=actual_page,
                    source_type=source_type,
                    verbatim_excerpt=para[:300],
                    extracted_parameters={"table_caption": table_matches[0].strip()},
                    document_title=document_title,
                    doi=doi,
                    confidence=0.9,
                )
            )

    return cards


def extract_evidence_from_pdf(
    pdf_source: Union[str, Path, bytes],
    document_title: str = "",
    doi: Optional[str] = None,
) -> List[EvidenceCard]:
    """
    Extract structured mechanics evidence cards from a PDF document.
    Parses all pages and attaches exact page numbers to every card.
    """
    pages = extract_pages_from_pdf(pdf_source)
    all_cards: List[EvidenceCard] = []

    for page_no, page_text in pages:
        page_cards = extract_evidence_from_text(
            page_text,
            document_title=document_title,
            doi=doi,
            page_number=page_no,
            source_type="pdf",
        )
        all_cards.extend(page_cards)

    return all_cards


