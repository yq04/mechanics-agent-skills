"""
Unit tests for the complete 7-Gate Scientific Integrity Pipeline (G1~G7).
"""

from pathlib import Path
import numpy as np
import pytest

from mechanics_skills.integrity import (
    run_integrity_pipeline,
    ConventionRegistry,
    create_data_provenance,
)


def test_run_integrity_pipeline_all_pass():
    """Verify that a compliant manuscript with data refs passes all integrity gates."""
    clean_text = (
        "# Mode I Fracture Analysis\n"
        "We consider an isotropic elastic material with Young's modulus E = 70 GPa and Poisson's ratio nu = 0.33.\n"
        "The governing equation \\nabla \\cdot \\sigma = 0 is satisfied.\n"
        "Crack faces are traction-free as shown in \\cite{Rice1968}.\n"
        "Results are verified against the canonical analytical Westergaard benchmark solution.\n"
        "Mesh convergence demonstrates grid independence.\n"
    )
    data_refs = [{"x": [0, 1], "sif": [1.0, 1.05]}]
    conv = ConventionRegistry()

    result = run_integrity_pipeline(clean_text, data_refs=data_refs, conventions=conv)

    assert result["status"] == "pass"
    assert result["readiness"] == "ready_for_author_review"
    assert len(result["data_provenances"]) == 1

    gates = result["gates"]
    assert gates["G1"]["status"] == "pass"
    assert gates["G2"]["status"] == "pass"
    assert gates["G3"]["status"] == "pass"
    assert gates["G4"]["status"] == "pass"
    assert gates["G5"]["status"] == "pass"
    assert gates["G6"]["status"] == "pass"
    assert gates["G7"]["status"] == "pass"


def test_gate_g1_stiffness_violation_and_sif_mismatch():
    """Verify G1 gate flags non-positive definite matrix and SIF factor anomalies."""
    text = "Linear elastic fracture study."
    # Non-positive definite stiffness matrix
    bad_C = np.eye(6) * 100.0
    bad_C[0, 0] = -50.0

    res_matrix = run_integrity_pipeline(text, options={"stiffness_matrix": bad_C})
    assert res_matrix["gates"]["G1"]["status"] == "fail"
    assert res_matrix["readiness"] == "blocked"

    # SIF sqrt(pi) factor discrepancy
    res_sif = run_integrity_pipeline(text, options={"sif_val": 1.7725, "baseline_val": 1.00})
    assert any("sqrt(pi)" in f["message"] for f in res_sif["gates"]["G1"]["findings"])


def test_gate_g2_abstract_source_and_uncited_claims():
    """Verify G2 gate flags abstract sources as critical and uncited claims as warnings."""
    # 1. Abstract source
    res_abs = run_integrity_pipeline("Full paper text.", options={"source_is_abstract": True})
    assert res_abs["gates"]["G2"]["status"] == "fail"
    assert res_abs["readiness"] == "blocked"

    # 2. Uncited literature claims
    uncited_text = "Previous studies indicate that crack growth occurs along grain boundaries."
    res_uncited = run_integrity_pipeline(uncited_text)
    assert res_uncited["gates"]["G2"]["status"] == "unknown"
    assert any("formal citations" in f["message"] for f in res_uncited["gates"]["G2"]["findings"])


def test_gate_g3_provenance_and_missing_data_warnings():
    """Verify G3 gate verifies cryptographic data provenance and flags missing raw data."""
    # Manuscript claiming Figure 1 results without data_refs
    text = "The variation of SIF is depicted in Figure 1 and Table 2."
    res = run_integrity_pipeline(text, data_refs=None)
    assert any("raw data provenance" in f["message"] for f in res["gates"]["G3"]["findings"])

    # Attached data_refs generates provenance
    res_with_data = run_integrity_pipeline(text, data_refs=[[1.0, 2.0, 3.0]])
    assert len(res_with_data["data_provenances"]) == 1
    assert len(res_with_data["data_provenances"][0]["sha256"]) == 64


def test_gate_g4_benchmark_self_referential():
    """Verify G4 gate blocks self-referential validation against author's own simulation."""
    text = "The computational model was verified against our own earlier simulation code."
    res = run_integrity_pipeline(text)
    assert res["gates"]["G4"]["status"] == "fail"
    assert res["readiness"] == "blocked"
    assert any("Self-referential validation" in f["message"] for f in res["gates"]["G4"]["findings"])


def test_gate_g5_bug_as_discovery():
    """Verify G5 gate detects numerical mesh singularity framed as new physics."""
    text = "The mesh singularity reveals a new physics of infinite stress concentration."
    res = run_integrity_pipeline(text)
    assert res["gates"]["G5"]["status"] == "fail"
    assert res["readiness"] == "blocked"
    assert any("numerical bug/singularity" in f["message"] for f in res["gates"]["G5"]["findings"])


def test_gate_g6_plane_assumption_contradiction():
    """Verify G6 gate flags contradiction between plane strain and effective modulus E."""
    # Plane strain with E' = E
    text_strain = "Under plane strain conditions, the effective modulus E' = E is used in calculations."
    res_strain = run_integrity_pipeline(text_strain)
    assert res_strain["gates"]["G6"]["status"] == "fail"
    assert res_strain["readiness"] == "blocked"

    # Plane stress with E' = E/(1 - nu^2)
    text_stress = "Under plane stress conditions, the effective modulus E' = E / (1 - \\nu^2) is used."
    res_stress = run_integrity_pipeline(text_stress)
    assert res_stress["gates"]["G6"]["status"] == "fail"
    assert res_stress["readiness"] == "blocked"


def test_gate_g7_scope_assumption_leakage():
    """Verify G7 gate detects applying isotropic Hooke's law to transversely isotropic solids."""
    text = (
        "We model a transversely isotropic composite lamina where the shear modulus "
        "is given by G = E / (2 ( 1 + \\nu ))."
    )
    res = run_integrity_pipeline(text)
    assert res["gates"]["G7"]["status"] == "fail"
    assert res["readiness"] == "blocked"
    assert any("Isotropic relation" in f["message"] for f in res["gates"]["G7"]["findings"])
