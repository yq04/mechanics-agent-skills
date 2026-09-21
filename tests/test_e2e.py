"""
End-to-End Integration Test for Mechanics Agent Skills Suite.
Simulates a full research lifecycle:
Search -> Screening -> Citation Main Path -> Evidence Extraction -> Synthesis Matrix -> BibTeX -> PRISMA Flowchart.
"""

from mechanics_skills.models import PaperRecord
from mechanics_skills.search import expand_mechanics_query
from mechanics_skills.screening import screen_paper, PRISMACounter
from mechanics_skills.citations import snowball_citations, extract_main_path, generate_mermaid_citation_network
from mechanics_skills.extraction import extract_evidence_from_text
from mechanics_skills.writing import (
    generate_prisma_mermaid,
    generate_evidence_matrix_markdown,
    generate_review_draft_sections,
)
from mechanics_skills.bibtex import paper_to_bibtex


def test_complete_mechanics_research_lifecycle():
    # 1. Query Expansion
    expanded = expand_mechanics_query("TI crack interaction SIF")
    assert any("transversely isotropic" in q for q in expanded)
    assert any("stress intensity factor" in q for q in expanded)

    # 2. Simulated Identified Papers
    p1 = PaperRecord(
        title="Exact Solution for Coplanar Penny-Shaped Cracks in Transversely Isotropic Media",
        doi="10.1016/j.engfracmech.2021.1001",
        authors=["A. Elastician", "B. Mechanician"],
        year=2021,
        journal="Engineering Fracture Mechanics",
        citations=45,
        abstract="We present exact potential theory solutions for penny-shaped cracks in transversely isotropic elastic media using Fabrikant potentials to determine Mode I stress intensity factors K_I and COD fields w(r).",
        sources=["crossref", "openalex"]
    )
    p2 = PaperRecord(
        title="Cellular Cavitation in Soft Biological Tissues",
        doi="10.1016/j.bio.2022.2002",
        authors=["C. Biologist"],
        year=2022,
        journal="Biomaterials",
        citations=12,
        abstract="In vivo study of cavitation in soft hydrogels under non-elastic deformation.",
        sources=["openalex"]
    )
    p3 = PaperRecord(
        title="Interaction between parallel elliptical cracks under remote tension",
        doi="10.1007/s10409-019-3003",
        authors=["D. Researcher"],
        year=2019,
        journal="Acta Mechanica Sinica",
        citations=28,
        abstract="Boundary element analysis of non-coplanar elliptical cracks in isotropic solids comparing with Kachanov self-consistent method.",
        sources=["crossref"]
    )

    # 3. Screening & Scoring
    counter = PRISMACounter(identified=3, duplicates_removed=0)
    counter.record_identification(0)
    res1 = screen_paper(p1)
    res2 = screen_paper(p2)
    res3 = screen_paper(p3)

    assert res1.total_score >= 7 and res1.category == "Included / Priority"
    assert res2.total_score <= 3 and res2.category == "Excluded"
    assert 4 <= res3.total_score <= 6 and res3.category == "Contextual / Background"

    counter.record_screening_result(res1)
    counter.record_screening_result(res2)
    counter.record_screening_result(res3)

    assert counter.included == 1
    assert counter.screened_excluded == 1

    # 4. Citation Network & Main Path & Mermaid
    graph = {
        "nodes": {
            "p_seed": {"title": "Foundational Potential Theory", "year": 1989, "citations": 150, "doi": "10.1007/seed", "authors": ["V. Fabrikant"]},
            "p_mid": {"title": "Transversely Isotropic Crack Boundary Layer", "year": 2005, "citations": 80, "doi": "10.1016/mid", "authors": ["X. Li"]},
            p1.doi: {"title": p1.title, "year": p1.year, "citations": p1.citations, "doi": p1.doi, "authors": p1.authors},
        },
        "edges": [
            {"source": "p_seed", "target": "p_mid", "type": "forward"},
            {"source": "p_mid", "target": p1.doi, "type": "forward"},
        ]
    }
    main_paths = extract_main_path(graph)
    assert len(main_paths) >= 1

    mermaid_citation = generate_mermaid_citation_network(graph)
    assert "graph TD" in mermaid_citation or "flowchart TD" in mermaid_citation
    assert "Foundational Potential Theory" in mermaid_citation or "Fabrikant" in mermaid_citation

    # 5. Evidence Extraction from Text
    paper_text = """
    We consider a transversely isotropic elastic medium with engineering moduli E1 = 120 GPa, E3 = 80 GPa, nu12 = 0.25.
    The defect consists of a penny-shaped crack of radius a subjected to uniform internal pressure p_0.
    Using Fabrikant elementary potentials, the governing boundary condition leads to the exact closed-form
    Mode I stress intensity factor:
    K_I = 2 * p_0 * sqrt(a / pi)
    The crack opening displacement w(r) along the crack face is derived analytically.
    Numerical validation against standard BEM results shows relative error below 0.05%.
    """
    cards = extract_evidence_from_text(paper_text, document_title=p1.title, doi=p1.doi, page_number=1)
    assert len(cards) >= 3
    card_types = [c.element_type for c in cards]
    assert "constitutive" in card_types
    assert "geometry" in card_types
    assert "potential" in card_types or "formula" in card_types

    # 6. Synthesis Matrix Generation
    card_dicts = [c.to_dict() for c in cards]
    matrix_md = generate_evidence_matrix_markdown(card_dicts)
    assert "| Study / Paper | Page | Category | Extracted Mechanics Parameters & Formulas | Confidence |" in matrix_md
    assert "transversely isotropic" in matrix_md.lower()

    # 7. PRISMA Flowchart Mermaid Generation
    prisma_mermaid = generate_prisma_mermaid(counter)
    assert "flowchart TD" in prisma_mermaid
    assert "Records screened" in prisma_mermaid

    # 8. BibTeX Generation
    bib_entry = paper_to_bibtex(p1)
    assert "@article{Elastician2021" in bib_entry
    assert "doi = {" + p1.doi + "}" in bib_entry

    # 9. Review Draft Synthesis
    draft = generate_review_draft_sections([p1, p3], card_dicts, counter=counter)
    assert "## 1. Introduction and Mechanical Scope" in draft
    assert "## 4. Evidence Synthesis Matrix" in draft
    assert "## 5. Identified Research Gaps" in draft
    assert "## 6. PRISMA-ScR Review Flow" in draft







