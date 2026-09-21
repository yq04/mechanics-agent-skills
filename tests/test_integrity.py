"""
Unit tests for core integrity foundation (provenance, constitutive admissibility, SIF normalization).
"""

from pathlib import Path
import numpy as np
import pytest

from mechanics_skills.integrity import (
    Finding,
    ConventionRegistry,
    DataProvenance,
    audit_data_provenance,
    create_data_provenance,
    check_constitutive_admissibility,
    check_sif_normalization,
)


def test_data_provenance_hashing(tmp_path):
    """Verify cryptographic SHA-256 hashing across strings, dicts, arrays, and files."""
    # 1. String and bytes hashing
    h_str = audit_data_provenance("elasticity benchmark")
    h_bytes = audit_data_provenance(b"elasticity benchmark")
    assert h_str == h_bytes
    assert len(h_str) == 64

    # 2. Key-order invariant dict hashing
    d1 = {"a": 100, "b": [1, 2, 3], "nested": {"c": "stress"}}
    d2 = {"nested": {"c": "stress"}, "b": [1, 2, 3], "a": 100}
    assert audit_data_provenance(d1) == audit_data_provenance(d2)

    # 3. File hashing
    sample_file = tmp_path / "raw_data.csv"
    sample_file.write_text("x,y,sif\n0.0,0.0,1.05\n0.5,0.0,1.12\n", encoding="utf-8")
    h_file = audit_data_provenance(str(sample_file))
    assert len(h_file) == 64

    # 4. DataProvenance dataclass creation
    prov = create_data_provenance(d1, source_path="data/test.json")
    assert prov.sha256 == audit_data_provenance(d1)
    assert prov.source_path == "data/test.json"
    assert prov.generation_timestamp is not None
    assert prov.to_dict()["sha256"] == prov.sha256


def test_constitutive_admissibility_valid_isotropic():
    """Verify that a standard isotropic stiffness matrix is fully admissible."""
    # Aluminum parameters: E = 70 GPa, nu = 0.33
    lam = 51.106
    mu = 26.315
    c11 = lam + 2 * mu
    c12 = lam
    c44 = mu

    C_iso = [
        [c11, c12, c12, 0, 0, 0],
        [c12, c11, c12, 0, 0, 0],
        [c12, c12, c11, 0, 0, 0],
        [0, 0, 0, c44, 0, 0],
        [0, 0, 0, 0, c44, 0],
        [0, 0, 0, 0, 0, c44],
    ]

    findings = check_constitutive_admissibility(C_iso, symmetry="isotropic")
    assert len(findings) == 0


def test_constitutive_admissibility_asymmetric():
    """Verify that an asymmetric stiffness matrix triggers a critical G1 finding."""
    C_asym = np.eye(6) * 100.0
    C_asym[0, 1] = 50.0
    C_asym[1, 0] = 20.0  # Asymmetry

    findings = check_constitutive_admissibility(C_asym, symmetry="isotropic")
    assert any(f.severity == "critical" and "major symmetry" in f.message for f in findings)


def test_constitutive_admissibility_non_positive_definite():
    """Verify that a stiffness matrix with non-positive eigenvalues triggers a critical G1 finding."""
    C_non_pos = np.eye(6) * 100.0
    C_non_pos[0, 0] = -10.0  # Negative diagonal / negative eigenvalue

    findings = check_constitutive_admissibility(C_non_pos, symmetry="isotropic")
    assert any(f.severity == "critical" and "positive definite" in f.message for f in findings)


def test_constitutive_admissibility_non_square():
    """Verify that a non-square matrix triggers a critical shape finding."""
    C_bad_shape = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    findings = check_constitutive_admissibility(C_bad_shape)
    assert any(f.severity == "critical" and "square" in f.message for f in findings)


def test_constitutive_admissibility_symmetry_violation():
    """Verify that an orthotropic or arbitrary matrix fails isotropic constraint checks."""
    C_ortho = np.diag([100.0, 80.0, 60.0, 30.0, 25.0, 20.0])
    findings = check_constitutive_admissibility(C_ortho, symmetry="isotropic")
    assert any(f.category == "G7" and "isotropic symmetry constraints" in f.message for f in findings)


def test_sif_normalization_valid():
    """Verify that normal SIF ratios pass without critical findings."""
    findings = check_sif_normalization(sif_val=1.05, baseline_val=1.00)
    assert len(findings) == 0


def test_sif_normalization_zero_baseline():
    """Verify that a zero baseline triggers a critical finding."""
    findings = check_sif_normalization(sif_val=1.05, baseline_val=0.00)
    assert any(f.severity == "critical" and "zero" in f.message for f in findings)


def test_sif_normalization_sqrt_pi_mismatch():
    """Verify that SIF ratios close to sqrt(pi) or 1/sqrt(pi) trigger warning findings."""
    # SIF ratio ~ 1.772
    findings_hi = check_sif_normalization(sif_val=1.7725, baseline_val=1.00)
    assert any(f.severity == "warning" and "sqrt(pi)" in f.message for f in findings_hi)

    # SIF ratio ~ 0.564
    findings_lo = check_sif_normalization(sif_val=0.564, baseline_val=1.00)
    assert any(f.severity == "warning" and "1/sqrt(pi)" in f.message for f in findings_lo)


def test_sif_normalization_negative_mode_i():
    """Verify that negative Mode I SIF under tensile loading triggers a warning."""
    findings = check_sif_normalization(sif_val=-0.45, baseline_val=1.00)
    assert any(f.severity == "warning" and "negative" in f.message for f in findings)


def test_convention_registry_roundtrip():
    """Verify ConventionRegistry dataclass serialization and defaults."""
    reg = ConventionRegistry(
        stress_components="cauchy",
        sign_convention="tension_positive",
        sif_normalization="standard",
        displacement_definition="single_side_w",
    )
    d = reg.to_dict()
    assert d["sign_convention"] == "tension_positive"
    assert d["sif_normalization"] == "standard"

    reg2 = ConventionRegistry.from_dict(d)
    assert reg2.sign_convention == reg.sign_convention
    assert reg2.unit_scales["stress"] == "MPa"
