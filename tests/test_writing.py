"""
Unit tests for PRISMA flowchart, Evidence Synthesis Matrix, Academic Review drafting, and BibTeX.
"""

import pytest

from mechanics_skills.models import PaperRecord
from mechanics_skills.screening import PRISMACounter
from mechanics_skills.bibtex import (
    generate_citekey,
    paper_to_bibtex,
    papers_to_bibtex,
    parse_bibtex_entry,
)
from mechanics_skills.writing import (
    generate_prisma_mermaid,
    generate_evidence_matrix_markdown,
    generate_review_draft_sections,
)


def test_generate_prisma_mermaid():
    """Verify that PRISMA-ScR flowchart generates valid Mermaid with accurate counters."""
    counter = PRISMACounter(
        identified=120,
        duplicates_removed=20,
        screened=100,
        screened_excluded=75,
        assessed_eligibility=25,
        eligibility_excluded=8,
        included=17,
    )
    counter.exclusion_reasons["Pure commercial FEA"] = 50
    counter.exclusion_reasons["Biomedical context"] = 25

    flowchart = generate_prisma_mermaid(counter)
    assert "flowchart TD" in flowchart
    assert "subgraph Identification" in flowchart
    assert "subgraph Screening" in flowchart
    assert "subgraph Eligibility" in flowchart
    assert "subgraph Included" in flowchart
    assert "(n = 120)" in flowchart
    assert "(n = 20)" in flowchart
    assert "(n = 100)" in flowchart
    assert "(n = 17)" in flowchart
    assert "Pure commercial FEA" in flowchart


def test_generate_evidence_matrix_markdown():
    """Verify Markdown evidence synthesis table formatting and pipe escaping."""
    evidence = [
        {
            "document_title": "Fabrikant 1989 Paper",
            "doi": "10.1016/sample.fab",
            "page_number": 14,
            "element_type": "formula",
            "extracted_parameters": {"SIF": "K_I = 2 * p0 * sqrt(a / pi)"},
            "confidence": 0.95,
        },
        {
            "document_title": "Collins 1963 Study | Benchmark",
            "doi": "10.1098/sample.col",
            "page_number": 8,
            "element_type": "benchmark",
            "extracted_parameters": {"table_caption": "Table 1: Collins 14 cases"},
            "confidence": 0.90,
        },
    ]

    table_md = generate_evidence_matrix_markdown(evidence)
    assert "| Study / Paper | Page | Category | Extracted Mechanics Parameters & Formulas | Confidence |" in table_md
    assert "[Fabrikant 1989 Paper](https://doi.org/10.1016/sample.fab)" in table_md
    assert "14" in table_md
    assert "Formula" in table_md
    # Check pipe escaping
    assert "&#124;" in table_md


def test_generate_review_draft_sections():
    """Verify synthesis review draft generation with research gaps and bibliography."""
    papers = [
        PaperRecord(
            title="Penny crack in transversely isotropic medium",
            authors=["Fabrikant VI", "Karapetian E"],
            year=1989,
            doi="10.1016/sample.fab",
            abstract="Transversely isotropic potential solution."
        ),
        PaperRecord(
            title="Classical 2D isotropic crack BEM",
            authors=["Betti E"],
            year=1975,
            doi="10.1007/sample.bet",
            abstract="Isotropic linear elasticity."
        )
    ]
    evidence = [
        {
            "document_title": "Penny crack in transversely isotropic medium",
            "page_number": 5,
            "element_type": "formula",
            "extracted_parameters": {"SIF": "K_I = 2 * p0 * sqrt(a / pi)"},
            "confidence": 0.95
        }
    ]
    counter = PRISMACounter(identified=2, duplicates_removed=0, screened=2, included=2)

    draft = generate_review_draft_sections(papers, evidence, counter=counter)
    assert "# Scoping Review:" in draft
    assert "## 1. Introduction and Mechanical Scope" in draft
    assert "## 2. Theoretical Formulations & Potential Methods" in draft
    assert "## 3. Defect Geometries & Interaction Mechanisms" in draft
    assert "## 4. Evidence Synthesis Matrix" in draft
    assert "## 5. Identified Research Gaps & Open Analytical Challenges" in draft
    assert "## 6. PRISMA-ScR Review Flowchart" in draft
    assert "## 7. Selected Bibliography" in draft
    assert "Fabrikant1989" in draft


def test_bibtex_generation_and_roundtrip():
    """Verify BibTeX generation, collision handling, and roundtrip parsing."""
    p1 = PaperRecord(
        title="Exact solution of penny-shaped crack in TI medium",
        authors=["Fabrikant, V. I."],
        year=1989,
        journal="Int. J. Solids Struct.",
        doi="10.1016/0020-7683(89)90001-X",
    )
    p2 = PaperRecord(
        title="Another work on TI cracks",
        authors=["Fabrikant, V. I."],
        year=1989,
        journal="J. Appl. Mech.",
        doi="10.1115/1.123456",
    )

    # 1. Single entry
    b1 = paper_to_bibtex(p1)
    assert "@article{Fabrikant1989," in b1
    assert "title = {Exact solution of penny-shaped crack in TI medium}" in b1

    # 2. Collision resolution
    bib_all = papers_to_bibtex([p1, p2])
    assert "@article{Fabrikant1989," in bib_all
    assert "@article{Fabrikant1989a," in bib_all

    # 3. Round-trip parsing
    entries = parse_bibtex_entry(bib_all)
    assert len(entries) == 2
    assert entries[0]["ID"] == "Fabrikant1989"
    assert entries[1]["ID"] == "Fabrikant1989a"
    assert entries[0]["doi"] == "10.1016/0020-7683(89)90001-X"
