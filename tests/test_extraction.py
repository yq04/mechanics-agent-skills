"""
Unit tests for mechanics evidence and formula extraction from text and PDF documents.
"""

from pathlib import Path
import pytest

from mechanics_skills.extraction import (
    extract_evidence_from_text,
    extract_evidence_from_pdf,
    EvidenceCard,
)


def test_extract_evidence_from_text_all_categories():
    """Verify that all 5 mechanics categories are extracted from representative literature text."""
    sample_text = """
    A transversely isotropic elastic medium Cadmium Selenide is investigated.
    The elastic stiffness constants are measured as:
    c11 = 74.1 GPa, c12 = 45.2 GPa, c13 = 39.3 GPa, c33 = 83.6 GPa, c44 = 13.2 GPa.
    The engineering Poisson ratio is nu = 0.28.

    Consider an isolated planar penny-shaped crack of radius a = 2.5 mm embedded in the isotropic plane.
    The crack faces are subjected to uniform internal pressure p(r) = p0 under traction-free boundary conditions at infinity.

    By employing the Fabrikant potential representation, the 3D boundary value problem reduces to an elementary Abel integral.
    The closed-form Mode I stress intensity factor at the crack border is obtained as:
    K_I = (2 / pi) * p0 * sqrt(pi * a).

    The crack opening displacement across the crack face is given by:
    w(r) = (4 * (1 - nu^2) / (pi * E)) * p0 * sqrt(a^2 - r^2).

    Table 2: Normalized stress intensity factor ratio K_I / K_0 for various crack spacings.
    Numerical results are compared against Collins benchmark solutions with high precision.
    """

    cards = extract_evidence_from_text(
        sample_text,
        document_title="Fabrikant TI Penny Crack",
        doi="10.1016/sample.extract",
        page_number=3
    )

    assert len(cards) >= 5
    types = {c.element_type for c in cards}
    assert "constitutive" in types
    assert "geometry" in types
    assert "potential" in types
    assert "formula" in types
    assert "benchmark" in types

    # Inspect specific extractions
    c_card = next(c for c in cards if c.element_type == "constitutive")
    assert c_card.page_number == 3
    assert "transversely isotropic" in c_card.extracted_parameters.get("symmetry", [])
    assert c_card.extracted_parameters.get("stiffness_constants", {}).get("c11") == "74.1"

    g_card = next(c for c in cards if c.element_type == "geometry")
    assert "penny-shaped crack" in g_card.extracted_parameters.get("defect_type", [])
    assert g_card.extracted_parameters.get("dimensions", {}).get("radius_or_axis") == "2.5"

    p_card = next(c for c in cards if c.element_type == "potential")
    assert any("Fabrikant" in rep for rep in p_card.extracted_parameters.get("representations", []))

    f_cards = [c for c in cards if c.element_type == "formula"]
    assert any("SIF" in c.extracted_parameters.get("formula_candidates", {}) for c in f_cards)
    assert any("COD" in c.extracted_parameters.get("formula_candidates", {}) for c in f_cards)

    b_card = next(c for c in cards if c.element_type == "benchmark")
    assert "Table 2" in b_card.extracted_parameters.get("table_caption", "")


def test_extract_evidence_from_pdf_multipage(tmp_path):
    """Create a minimal 2-page test PDF using PyMuPDF and verify page-anchored evidence extraction."""
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF not installed")

    pdf_file = tmp_path / "test_mechanics.pdf"
    doc = fitz.open()

    # Page 1: Constitutive and Geometry
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Transversely isotropic medium with stiffness constants c11 = 80.0 GPa and c33 = 95.0 GPa.\n"
        "A penny-shaped crack of radius a = 4.0 mm is subjected to internal pressure p0.\n"
    )

    # Page 2: Potentials and Formulas
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "Using Fabrikant potential representation, the stress intensity factor is derived as:\n"
        "K_I = 2 * p0 * sqrt(a / pi).\n"
        "Table 1: Normalized stress intensity factor ratio K_I / K_0 benchmark comparison.\n"
    )

    doc.save(str(pdf_file))
    doc.close()

    # Extract evidence from the generated PDF
    cards = extract_evidence_from_pdf(pdf_file, document_title="Multi-page TI Crack Paper", doi="10.1016/sample.pdf")
    assert len(cards) >= 3

    # Check that page 1 cards have page_number == 1
    p1_cards = [c for c in cards if c.page_number == 1]
    assert len(p1_cards) >= 1
    assert any(c.element_type in ("constitutive", "geometry") for c in p1_cards)

    # Check that page 2 cards have page_number == 2
    p2_cards = [c for c in cards if c.page_number == 2]
    assert len(p2_cards) >= 1
    assert any(c.element_type in ("potential", "formula", "benchmark") for c in p2_cards)


def test_extract_evidence_text_fallback(tmp_path):
    """Test fallback when a text file is passed to extract_evidence_from_pdf."""
    txt_file = tmp_path / "note.txt"
    txt_file.write_text(
        "Isotropic elastic material with E = 210 GPa and nu = 0.3.\n"
        "A crack under uniform tension with SIF formula K_I = sigma * sqrt(pi * a).\n",
        encoding="utf-8"
    )

    cards = extract_evidence_from_pdf(txt_file, document_title="Fallback Note")
    assert len(cards) >= 1
    assert cards[0].page_number == 1
