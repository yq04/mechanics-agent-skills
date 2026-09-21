---
name: mechanics-paper-reviewer
description: Simulated academic peer review and five-dimensional scientific soundness audit for solid mechanics, fracture mechanics, and continuum physics. Evaluates governing equation completeness, constitutive admissibility, boundary and interface conditions, independent benchmark validation and convergence, and physical mechanism interpretation. Supports journal profiles for JMPS, IJSS, EFM, and Acta Mechanica Sinica. Use when auditing mechanics manuscripts, evaluating scientific soundness, generating peer review reports, or verifying revision improvements.
metadata:
  version: "3.1.0"
  domain: "Solid Mechanics / Fracture Mechanics / Peer Review"
---

# Simulated Mechanics Peer Review & Five-Dimensional Soundness Audit

Evidence-anchored simulated peer review engine for solid mechanics, fracture mechanics, and elasticity manuscripts.
Evaluates research papers against a rigorous Five-Dimensional Soundness Checklist, applies tailored journal profile heuristics (JMPS, IJSS, EFM, AMS), tracks revision resolutions, and generates publication-grade peer review reports.

---

## 1. When to Use
- Pre-submission peer review of manuscripts targeted at mechanics journals.
- Auditing theoretical completeness (balance laws, potential representations, kinematics).
- Verifying boundary value problem well-posedness (traction-free crack faces, interface jump conditions, far-field conditions).
- Checking benchmark independence (ensuring numerical models are validated against independent analytical benchmarks rather than self-referential codes).
- Comparing revised manuscripts against previous review findings to generate an author revision ledger.

---

## 2. Five-Dimensional Soundness Framework

| Dimension | Mechanics Scope | Evaluation Focus |
|---|---|---|
| **D1: Governing Equations Completeness** | Balance of momentum, kinematics, potentials, PDE closure | Are coordinate systems, field equations, and potentials mathematically closed? |
| **D2: Constitutive, Symmetry & Admissibility** | Material symmetry, Hooke's law, strain energy positive-definiteness | Are stiffness tensors thermodynamically stable and symmetry axes defined? |
| **D3: Boundary & Interface Conditions** | Natural & essential boundary conditions, crack faces, interfaces | Are crack face conditions explicit (traction-free, contact, pressure)? |
| **D4: Validation, Convergence & Reproducibility** | Canonical benchmarks, mesh refinement, discretization errors | Is validation performed against independent analytical solutions? |
| **D5: Physical Interpretation & Mechanism** | Stress shielding, crack deflection, asymptotic singularity limits | Are observed trends explained by mechanics mechanisms rather than raw curves? |

---

## 3. Supported Journal Profiles
- **JMPS (Journal of the Mechanics and Physics of Solids)**: Priority on foundational theory, micromechanics, and physical mechanisms (D1, D2, D5).
- **IJSS (International Journal of Solids and Structures)**: Priority on solid mechanics, boundary formulations, and computational validation (D1, D3, D4).
- **EFM (Engineering Fracture Mechanics)**: Priority on fracture criteria, crack face conditions, and benchmark validation (D3, D4, D5).
- **Acta Mechanica Sinica (AMS)**: Comprehensive theoretical clarity and physical rigor (D1, D2, D4).
- **Generic**: Standard balanced evaluation across D1~D5.

---

## 4. CLI Commands

### Audit Manuscript Soundness
```bash
mechanics-peer-review audit manuscript.md --journal jmps --markdown review_report.md
```

### Prepare Review Task Package for Host Subagents
```bash
mechanics-peer-review prepare manuscript.md --journal jmps --output-dir artifacts/review_pkg
```

### Compare Revision Against Previous Review
```bash
mechanics-peer-review compare previous_review.json revised_manuscript.md --output comparison.json
```
