"""
Universal Solid Mechanics and Applied Mathematics literature search & query expansion.
"""

from typing import Any, Dict, List, Optional, Set
import re

from mechanics_skills.models import PaperRecord
from mechanics_skills.providers.arxiv import ArXivProvider
from mechanics_skills.providers.crossref import CrossrefProvider
from mechanics_skills.providers.openalex import OpenAlexProvider
from mechanics_skills.providers.semantic_scholar import SemanticScholarProvider
from mechanics_skills.identifiers import generate_dedup_key, fuzzy_title_match


# Universal solid mechanics and fracture mechanics taxonomy
MECHANICS_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "constitutive": {
        "isotropic": [
            "isotropic elasticity", "homogeneous isotropic", "classical elasticity"
        ],
        "transversely_isotropic": [
            "transversely isotropic", "transverse isotropy", "TI medium",
            "hexagonal crystal elasticity", "spherically isotropic"
        ],
        "orthotropic": [
            "orthotropic elasticity", "orthotropic medium", "orthotropy"
        ],
        "anisotropic": [
            "general anisotropic", "anisotropic elasticity", "triclinic medium",
            "monoclinic medium"
        ],
        "piezoelectric": [
            "piezoelectric", "electro-elastic", "magnetoelectroelastic", "smart materials"
        ],
        "functionally_graded": [
            "functionally graded", "FGM", "non-homogeneous elasticity"
        ],
        "viscoelastic": [
            "viscoelasticity", "fractional viscoelasticity", "creep relaxation"
        ],
        "poroelastic": [
            "poroelasticity", "Biot poroelasticity", "fluid-saturated porous media"
        ],
    },
    "geometry": {
        "penny_shaped_crack": [
            "penny-shaped crack", "circular crack", "3D disk crack", "penny crack"
        ],
        "elliptical_crack": [
            "elliptical crack", "elliptic crack", "planar elliptical crack"
        ],
        "coplanar_cracks": [
            "coplanar cracks", "collinear cracks", "multiple coplanar cracks"
        ],
        "parallel_cracks": [
            "parallel cracks", "non-coplanar parallel cracks", "stacked cracks"
        ],
        "interface_crack": [
            "interface crack", "bimaterial crack", "interfacial crack"
        ],
        "inclusion": [
            "elastic inclusion", "inhomogeneity", "Eshelby inclusion"
        ],
        "notch": [
            "V-notch", "U-notch", "re-entrant corner", "angular notch"
        ],
        "interacting_cracks": [
            "interacting cracks", "crack interaction", "multiple cracks", "crack cluster"
        ],
        "edge_crack": [
            "edge crack", "surface crack", "semi-infinite crack"
        ],
    },
    "method": {
        "potential_theory": [
            "potential theory", "Fabrikant potential", "Papkovich-Neuber",
            "Muskhelishvili potentials", "Boussinesq potential", "Green functions"
        ],
        "integral_equations": [
            "dual integral equations", "singular integral equations",
            "Fredholm integral equations", "Cauchy singular kernel"
        ],
        "integral_transforms": [
            "Hankel transform", "Fourier transform", "Mellin transform", "Laplace transform"
        ],
        "boundary_element": [
            "boundary element method", "BEM", "boundary integral equation method", "BIEM"
        ],
        "complex_potentials": [
            "complex variable method", "Kolosov-Muskhelishvili", "conformal mapping"
        ],
        "stroh_formalism": [
            "Stroh formalism", "sextic formalism", "Barnett-Lothe tensors"
        ],
        "asymptotic_expansions": [
            "asymptotic expansion", "matched asymptotics", "Williams expansion",
            "eigenfunction expansion"
        ],
        "kachanov_method": [
            "Kachanov method", "traction-free condition", "self-consistent method",
            "transmission matrix"
        ],
    },
    "fields": {
        "stress_intensity_factor": [
            "stress intensity factor", "SIF", "Mode I SIF", "Mode II SIF", "Mode III SIF"
        ],
        "crack_opening_displacement": [
            "crack opening displacement", "COD", "crack face displacement", "discontinuity jump"
        ],
        "t_stress": [
            "T-stress", "non-singular stress", "higher order stress terms"
        ],
        "energy_release_rate": [
            "energy release rate", "strain energy release rate", "Griffith energy"
        ],
        "j_integral": [
            "J-integral", "path-independent integral", "interaction integral", "M-integral"
        ],
        "interaction_matrix": [
            "interaction matrix", "cross-influence tensor", "transmission coefficients"
        ],
    },
}


def expand_mechanics_query(
    query: str, domain_filters: Optional[List[str]] = None
) -> List[str]:
    """
    Expand a base mechanics query using domain-specific taxonomy.
    Preserves the original query as the primary entry.
    Generates targeted academic search variants.
    """
    query_clean = query.strip()
    if not query_clean:
        return []

    q_lower = query_clean.lower()
    expanded_queries: List[str] = [query_clean]
    seen: Set[str] = {query_clean.lower()}

    domains = list(MECHANICS_TAXONOMY.keys())
    if domain_filters:
        filter_set = {d.strip().lower() for d in domain_filters}
        domains = [d for d in domains if d in filter_set]

    matched_expansions: List[str] = []
    for domain in domains:
        for concept, terms in MECHANICS_TAXONOMY[domain].items():
            concept_pattern = concept.replace("_", " ")
            has_match = False
            # Check concept name, any term in query, or broad keyword overlap
            if concept_pattern in q_lower or any(t.lower() in q_lower for t in terms):
                has_match = True
            elif any(w in q_lower for w in concept.split("_") if len(w) > 4):
                has_match = True

            if has_match:
                for term in terms:
                    if term.lower() not in q_lower:
                        matched_expansions.append(term)

    # 1. Direct term additions
    for term in matched_expansions[:4]:
        candidate = f"{query_clean} {term}"
        if candidate.lower() not in seen:
            seen.add(candidate.lower())
            expanded_queries.append(candidate)

    # 2. Acronym expansion
    abbrev_map = {
        r"\bTI\b": "transversely isotropic",
        r"\bSIF\b": "stress intensity factor",
        r"\bCOD\b": "crack opening displacement",
        r"\bBEM\b": "boundary element method",
        r"\bFGM\b": "functionally graded material",
    }
    for pat, expansion in abbrev_map.items():
        if re.search(pat, query_clean, re.IGNORECASE):
            candidate = re.sub(pat, expansion, query_clean, flags=re.IGNORECASE).strip()
            if candidate.lower() not in seen:
                seen.add(candidate.lower())
                expanded_queries.append(candidate)

    return expanded_queries


def search_literature(
    query: str,
    sources: Optional[List[str]] = None,
    limit_per_source: int = 10,
    expand: bool = False,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    domain_filters: Optional[List[str]] = None,
    client: Optional[Any] = None,
    silent: bool = True,
) -> List[PaperRecord]:
    """
    Multi-source literature search across Crossref, OpenAlex, arXiv, and Semantic Scholar.
    Optionally expands query with mechanics taxonomy and filters by publication year.
    """
    if sources is None:
        sources = ["crossref", "openalex", "arxiv"]

    queries = [query]
    if expand:
        queries = expand_mechanics_query(query, domain_filters=domain_filters)[:3]

    provider_map = {
        "crossref": CrossrefProvider(client=client),
        "openalex": OpenAlexProvider(client=client),
        "arxiv": ArXivProvider(client=client),
        "semantic_scholar": SemanticScholarProvider(client=client),
    }

    dedup_map: Dict[str, PaperRecord] = {}
    ordered_papers: List[PaperRecord] = []

    for q in queries:
        for src in sources:
            src_clean = src.strip().lower()
            if src_clean not in provider_map:
                continue
            prov = provider_map[src_clean]
            try:
                records = prov.search(q, limit=limit_per_source)
            except Exception:
                records = []

            for rec in records:
                if rec.year is not None:
                    if year_start is not None and rec.year < year_start:
                        continue
                    if year_end is not None and rec.year > year_end:
                        continue

                key = generate_dedup_key(rec)
                if key in dedup_map:
                    existing = dedup_map[key]
                    if src_clean not in existing.sources:
                        existing.sources.append(src_clean)
                    if not existing.doi and rec.doi:
                        existing.doi = rec.doi
                    if not existing.oa_url and rec.oa_url:
                        existing.oa_url = rec.oa_url
                    if rec.citations > existing.citations:
                        existing.citations = rec.citations
                    continue

                matched = False
                for existing in ordered_papers:
                    if fuzzy_title_match(rec.title, existing.title):
                        if src_clean not in existing.sources:
                            existing.sources.append(src_clean)
                        if not existing.doi and rec.doi:
                            existing.doi = rec.doi
                        if not existing.oa_url and rec.oa_url:
                            existing.oa_url = rec.oa_url
                        if rec.citations > existing.citations:
                            existing.citations = rec.citations
                        matched = True
                        break

                if not matched:
                    dedup_map[key] = rec
                    ordered_papers.append(rec)

    ordered_papers.sort(key=lambda p: p.citations or 0, reverse=True)
    return ordered_papers
