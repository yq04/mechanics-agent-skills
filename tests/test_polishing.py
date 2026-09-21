"""
Unit tests for Mechanics Paper Polishing & Notation Guard (Phase 7).
"""

import json
from pathlib import Path
import pytest

from mechanics_skills.polishing import (
    extract_protected_zones,
    detect_cliches,
    detect_notation_warnings,
    analyze_manuscript,
    prepare_polish_request,
    validate_edits,
    apply_edits,
)
from mechanics_skills.cli import polish_cli


def test_extract_protected_zones_all_types():
    """Verify that all mathematical environments, citations, code, units, and URLs are protected."""
    sample = (
        "# Formulation\n"
        "Consider an isotropic solid with Young's modulus 120 GPa and Poisson's ratio 0.33.\n"
        "The stress intensity factor is $K_I = 25.4\\text{ MPa}\\sqrt{m}$.\n"
        "The displacement satisfies \\( u_x = c \\sqrt{r} \\).\n"
        "\\begin{equation}\n"
        "\\sigma_{ij} = \\frac{K_I}{\\sqrt{2\\pi r}} f_{ij}(\\theta)\n"
        "\\end{equation}\n"
        "Refer to \\cite{Rice1968} and \\eqref{eq:crack} for details.\n"
        "Code implementation is available in \x60crack_tip.py\x60 or https://github.com/mechanics/crack.\n"
    )

    zones = extract_protected_zones(sample)
    types = {z.zone_type for z in zones}

    assert "unit_quantity" in types
    assert "math_inline" in types
    assert "math_display" in types
    assert "citation" in types
    assert "cross_ref" in types
    assert "code" in types
    assert "url" in types

    # Check SHA-256 uniqueness and accuracy
    for z in zones:
        assert len(z.sha256) == 64
        assert sample[z.start:z.end] == z.content


def test_detect_cliches_and_physical_alternatives():
    """Verify detection of AI fluff outside protected zones."""
    text = (
        "This work delves into the crack mechanics. It serves as a testament to the crucial interplay "
        "between microstructure and fracture toughness. Moreover, it fosters a rich tapestry of stress fields."
    )
    zones = extract_protected_zones(text)
    cliches = detect_cliches(text, zones)

    words_found = {c["word"] for c in cliches}
    assert "delve into" in words_found or "delve" in words_found
    assert "serves as a testament to" in words_found or "testament" in words_found
    assert "crucial" in words_found
    assert "interplay" in words_found
    assert "foster" in words_found
    assert "tapestry" in words_found
    assert "moreover" in words_found


def test_notation_guard_cod_and_sif():
    """Verify notation warnings for COD vs w, k_I vs K_I, and engineering shear."""
    ambiguous_text = (
        "The crack opening displacement COD is measured. Displacement w is also recorded. "
        "We denote the stress intensity factor as both K_I and k_I. "
        "Strains are gamma_xy and epsilon_xy."
    )
    warnings = detect_notation_warnings(ambiguous_text)
    fields = {w.field for w in warnings}

    assert "displacement_definition" in fields
    assert "sif_normalization" in fields
    assert "shear_strain_convention" in fields


def test_prepare_polish_request_contract():
    """Verify structured request package generation with needs_authoring status."""
    manuscript = "We delve into the analysis with $E = 100\\text{ GPa}$."
    analysis = analyze_manuscript(manuscript)
    req = prepare_polish_request(analysis)

    assert req["status"] == "needs_authoring"
    assert req["task_name"] == "mechanics_paper_polishing"
    assert "style_guidelines" in req
    assert "output_schema_expected" in req
    assert req["source_hash"] == analysis["source_hash"]


def test_validate_and_apply_edits_safe():
    """Verify that safe non-mathematical edits pass validation and apply correctly."""
    before = "This work delves into the crack problem."
    start = before.index("delves into")
    end = start + len("delves into")

    proposals = [{
        "edit_id": "prop_1",
        "start": start,
        "end": end,
        "original_text": "delves into",
        "replacement": "investigates",
        "category": "style",
        "reason": "Remove cliche",
    }]

    findings = validate_edits(before, proposals)
    assert len(findings) == 0

    after, diffs = apply_edits(before, proposals)
    assert after == "This work investigates the crack problem."
    assert len(diffs) == 1
    assert diffs[0]["applied"] is True


def test_validate_edits_blocks_protected_math():
    """Verify that attempting to modify or tamper with protected math triggers a critical finding."""
    before = "The stress is $\\sigma_0 = 100\\text{ MPa}$ at infinity."
    start = before.index("$\\sigma_0")
    end = before.index("MPa}$") + len("MPa}$")

    proposals = [{
        "edit_id": "prop_bad_math",
        "start": start,
        "end": end,
        "original_text": before[start:end],
        "replacement": "$\\sigma_0 = 200\\text{ MPa}$",
        "category": "formula_edit",
    }]

    findings = validate_edits(before, proposals)
    assert any(f.severity == "critical" and "protected" in f.message for f in findings)

    with pytest.raises(ValueError, match="critical integrity violations"):
        apply_edits(before, proposals)


def test_validate_edits_blocks_overlapping():
    """Verify that overlapping proposals are flagged as critical errors."""
    before = "This is a simple sentence for testing."
    proposals = [
        {"edit_id": "p1", "start": 0, "end": 10, "original_text": before[0:10], "replacement": "That was"},
        {"edit_id": "p2", "start": 5, "end": 15, "original_text": before[5:15], "replacement": "a clear"},
    ]
    findings = validate_edits(before, proposals)
    assert any(f.severity == "critical" and "overlaps" in f.message for f in findings)


def test_validate_edits_blocks_unauthorized_exactness():
    """Verify that edits claiming 'exact solution' or 'proved analytically' trigger critical findings."""
    before = "We obtain numerical results."
    start = before.index("numerical results")
    end = start + len("numerical results")
    proposals = [{
        "edit_id": "p_exact",
        "start": start,
        "end": end,
        "original_text": "numerical results",
        "replacement": "an exact solution proved analytically",
        "category": "claim_upgrade",
    }]
    findings = validate_edits(before, proposals)
    assert any(f.severity == "critical" and "exactness claim" in f.message for f in findings)


def test_polish_cli_workflow(tmp_path):
    """Verify full polish CLI commands (analyze, prepare, validate, apply)."""
    manuscript_file = tmp_path / "manuscript.md"
    manuscript_file.write_text(
        "# Introduction\nThis work delves into crack propagation with $K_I = 20\\text{ MPa}\\sqrt{m}$.\n",
        encoding="utf-8",
    )

    # 1. analyze
    analysis_file = tmp_path / "analysis.json"
    ret_analyze = polish_cli(["analyze", str(manuscript_file), "--output", str(analysis_file)])
    assert ret_analyze == 0
    assert analysis_file.is_file()

    # 2. prepare
    prep_dir = tmp_path / "prep_artifacts"
    ret_prep = polish_cli(["prepare", str(manuscript_file), "--output-dir", str(prep_dir)])
    assert ret_prep == 0
    assert (prep_dir / "polish_request.json").is_file()

    # 3. validate & apply
    orig_text = manuscript_file.read_text(encoding="utf-8")
    start = orig_text.index("delves into")
    end = start + len("delves into")
    proposals = {
        "proposals": [{
            "edit_id": "e01",
            "start": start,
            "end": end,
            "original_text": "delves into",
            "replacement": "analyzes",
            "category": "style",
        }]
    }
    prop_file = tmp_path / "proposals.json"
    prop_file.write_text(json.dumps(proposals), encoding="utf-8")

    ret_val = polish_cli(["validate", str(manuscript_file), str(prop_file)])
    assert ret_val == 0

    polished_file = tmp_path / "polished.md"
    diff_file = tmp_path / "diff.json"
    ret_apply = polish_cli(["apply", str(manuscript_file), str(prop_file), "--output", str(polished_file), "--diff", str(diff_file)])
    assert ret_apply == 0
    assert polished_file.is_file()
    assert "analyzes crack propagation" in polished_file.read_text(encoding="utf-8")
    assert "$K_I = 20\\text{ MPa}\\sqrt{m}$" in polished_file.read_text(encoding="utf-8")
