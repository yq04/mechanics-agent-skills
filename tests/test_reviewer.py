"""
Unit tests for Simulated Mechanics Peer Review & Integrity Audit (Phase 8).
"""

import json
from pathlib import Path
import pytest

from mechanics_skills.reviewer import (
    JOURNAL_PROFILES,
    get_journal_profile,
    audit_scientific_soundness,
    generate_review_report_markdown,
    compare_revision,
    prepare_review_package,
)
from mechanics_skills.cli import peer_review_cli


def test_journal_profiles_loading():
    """Verify loading of journal profiles and priority dimensions."""
    for jcode in ["jmps", "ijss", "efm", "acta_mech_sin", "generic"]:
        p = get_journal_profile(jcode)
        assert p["journal_code"] == jcode
        assert len(p["priority_dimensions"]) >= 3
        assert "rubric" in p
        assert p["policy_status"] == "provisional_heuristic"

    # Fallback to generic
    fallback = get_journal_profile("unknown_journal")
    assert fallback["journal_code"] == "generic"


def test_audit_scientific_soundness_incomplete():
    """Verify that an incomplete manuscript triggers major concerns in D1-D4."""
    incomplete_text = (
        "# Crack Study\n"
        "We simulate crack propagation under tension.\n"
        "Young's modulus is 70 GPa.\n"
        "Results are shown below.\n"
    )

    audit = audit_scientific_soundness(incomplete_text, journal="jmps")
    assert audit["overall_soundness"] in ("major_concerns", "incomplete")
    assert audit["major_concerns_count"] >= 2

    dims = audit["dimensions"]
    assert dims["D1_governing_equations"]["status"] == "concern"
    assert dims["D3_boundary_interface"]["status"] == "concern"
    assert dims["D4_validation_convergence"]["status"] == "concern"


def test_audit_scientific_soundness_sound():
    """Verify that a comprehensive, evidence-anchored manuscript achieves sound rating."""
    sound_text = (
        "# Equilibrium and Boundary Value Problem in Isotropic Elasticity\n"
        "Consider a 2D Cartesian coordinate system (x, y) centered at the crack.\n"
        "The balance of linear momentum governing the solid is \\nabla \\cdot \\sigma = 0.\n"
        "The material is isotropic with Young's modulus E = 70 GPa and Poisson's ratio nu = 0.33.\n"
        "The crack faces are traction-free: \\sigma_{yy}(x, 0) = 0 for |x| < a.\n"
        "Tensile far-field boundary conditions are applied at infinity.\n"
        "Validation against the independent analytical Westergaard benchmark shows agreement within 0.2%.\n"
        "A mesh refinement study confirms discretization convergence and grid independence.\n"
        "The observed toughening mechanism is attributed to crack tip stress shielding.\n"
    )

    audit = audit_scientific_soundness(sound_text, journal="jmps")
    assert audit["overall_soundness"] == "sound"
    assert audit["major_concerns_count"] == 0
    assert audit["minor_concerns_count"] == 0


def test_generate_review_report_markdown():
    """Verify Markdown review report format and required sections."""
    sample_text = (
        "# Crack Simulation\n"
        "We compute stresses near a crack in an elastic solid with E = 100 GPa.\n"
    )
    audit = audit_scientific_soundness(sample_text, journal="efm")
    report_md = generate_review_report_markdown(audit)

    assert "Simulated Peer Review Report" in report_md
    assert "Notice" in report_md
    assert "Engineering Fracture Mechanics" in report_md
    assert "Five-Dimensional Soundness Matrix" in report_md
    assert "Major Scientific Concerns" in report_md
    assert "Actionable Author Checklist" in report_md


def test_compare_revision_resolutions():
    """Verify that compare_revision identifies resolved vs persisting issues."""
    v1_text = "We compute crack growth with E = 70 GPa."
    review_v1 = audit_scientific_soundness(v1_text, journal="jmps")

    v2_text = (
        "In a Cartesian coordinate system (x, y), we formulate \\nabla \\cdot \\sigma = 0.\n"
        "The material is isotropic with E = 70 GPa and nu = 0.33.\n"
        "Crack faces are traction-free: \\sigma_{yy} = 0 on crack faces.\n"
        "Validated against the Westergaard analytical benchmark.\n"
        "Mesh refinement convergence is demonstrated.\n"
        "The physical mechanism is crack deflection.\n"
    )

    comp = compare_revision(review_v1, v2_text)
    assert comp["status"] in ("improved", "resolved")
    assert comp["resolved_count"] > 0
    assert comp["persisting_count"] == 0


def test_prepare_review_package():
    """Verify packaging of review task for subagents/host model."""
    text = "Crack tip study with E = 200 GPa."
    pkg = prepare_review_package(text, journal="ijss")

    assert pkg["status"] == "review_package_ready"
    assert pkg["journal"] == "ijss"
    assert "soundness_audit" in pkg
    assert len(pkg["source_hash"]) == 64


def test_peer_review_cli_workflow(tmp_path):
    """Verify peer review CLI commands (audit, prepare, compare, report)."""
    ms_file = tmp_path / "manuscript.md"
    ms_file.write_text(
        "# Fracture Study\nCartesian (x, y) frame with equilibrium \\nabla \\cdot \\sigma = 0.\n"
        "Isotropic material with E = 70 GPa, nu = 0.33.\n"
        "Traction-free crack faces.\nValidated against Westergaard benchmark.\n"
        "Mesh convergence verified. Physical mechanism: stress shielding.\n",
        encoding="utf-8",
    )

    # 1. audit
    audit_file = tmp_path / "audit.json"
    report_file = tmp_path / "report.md"
    ret_audit = peer_review_cli([
        "audit", str(ms_file),
        "--journal", "jmps",
        "--output", str(audit_file),
        "--markdown", str(report_file),
    ])
    assert ret_audit == 0
    assert audit_file.is_file()
    assert report_file.is_file()

    # 2. prepare
    prep_dir = tmp_path / "review_prep"
    ret_prep = peer_review_cli(["prepare", str(ms_file), "--journal", "jmps", "--output-dir", str(prep_dir)])
    assert ret_prep == 0
    assert (prep_dir / "package.json").is_file()
    assert (prep_dir / "review_draft.md").is_file()

    # 3. compare
    v1_audit_file = tmp_path / "v1_audit.json"
    v1_ms = tmp_path / "v1.md"
    v1_ms.write_text("Crack simulation with E = 70 GPa.\n", encoding="utf-8")
    peer_review_cli(["audit", str(v1_ms), "--output", str(v1_audit_file)])

    comp_file = tmp_path / "comp.json"
    ret_comp = peer_review_cli(["compare", str(v1_audit_file), str(ms_file), "--output", str(comp_file)])
    assert ret_comp == 0
    assert comp_file.is_file()

    # 4. report
    out_rep = tmp_path / "rendered_report.md"
    ret_rep = peer_review_cli(["report", str(audit_file), "--output", str(out_rep)])
    assert ret_rep == 0
    assert out_rep.is_file()
