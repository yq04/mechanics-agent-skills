# Mechanics Agent Skills: Capability Status & Dependency Mapping

> Document Version: 3.1.0  
> Date: 2026-09-21  
> Purpose: Explicit mapping of actual implemented features, runtime dependency tiers, verified vs. heuristic components, and known boundaries.

---

## 1. Runtime Dependency Tiers

| Tier | Packages | Modules Supported | Fallback / Behavior when Missing |
|---|---|---|---|
| **Base Microkernel** (Zero External Dependencies) | Python Stdlib only (`urllib`, `sqlite3`, `dataclasses`, `json`, `re`, `hashlib`, `math`, `pathlib`) | Literature search, 5D screening, citation snowballing, text extraction, manuscript polishing analysis, peer review audit preparation, integrity checking. | Always operational on Python 3.10+. |
| **`[figure]` Extra** | `matplotlib>=3.8`, `numpy>=1.26` | `mechanics_skills.figure` (vector SVG/PDF & 300+ DPI PNG rendering, colormap audits). | Figure validation and spec templating operate on stdlib; rendering exits with diagnostic error code 2 if extras are missing. |
| **`[pdf]` Extra** | `PyMuPDF>=1.24` | Accelerated PDF binary stream parsing and spatial coordinate bounding-box extraction. | Falls back to basic text parsing or requests text/OCR input. |
| **`[http]` Extra** | `httpx>=0.27` | High-throughput asynchronous HTTP transport and connection pooling. | Falls back seamlessly to `urllib.request` transport with rate limiting. |

---

## 2. Journal Profiles Matrix

Simulated peer review profiles are calibrated against the following journal criteria:

| Profile Key | Journal Title | Publisher | Focus Areas | Status |
|---|---|---|---|---|
| **`jmps`** | *Journal of the Mechanics and Physics of Solids* | Elsevier | Fundamental theoretical breakthroughs, mathematical rigor, constitutive proofs. | Active (Calibrated) |
| **`ijss`** | *International Journal of Solids and Structures* | Elsevier | Structural mechanics, analytical/numerical formulation consistency. | Active (Calibrated) |
| **`efm`** | *Engineering Fracture Mechanics* | Elsevier | Crack tip fields, fatigue, experimental & asymptotic fracture mechanics. | Active (Calibrated) |
| **`acta_mech_sin`**| *Acta Mechanica Sinica* | Springer / CSTAM | Solid mechanics, applied elasticity, asymptotic methods. | Active (Calibrated) |
| **`generic`** | Generic Mechanics Profile | General | Baseline five-dimensional soundness checks. | Active (Default Fallback) |

*Note*: Journal profiles for *IJF* (*International Journal of Fracture*) and *CMAME* (*Computer Methods in Applied Mechanics and Engineering*) are mapped to the generic/calibrated solid mechanics heuristics until dedicated profiles are finalized.

---

## 3. Seven-Gate Scientific Integrity Pipeline

| Gate | Focus | Evaluation Method | Operational Status |
|---|---|---|---|
| **G1** | Constitutive Admissibility | Positive-definiteness check of stiffness/compliance matrices ($C_{ijkl}$); $r^{-1/2}$ asymptotic stress intensity scaling. | Active |
| **G2** | Evidence Grounding | Differentiates `abstract` from real `pdf_page` citations; flags unverified or hallucinated claims. | Active |
| **G3** | Provenance Traceability | Computes deterministic SHA-256 digests matching raw simulation inputs to figure specifications. | Active |
| **G4** | Benchmark Independence | Differentiates internal solver self-consistency tests from canonical analytical solutions (Sneddon, Westergaard). | Active |
| **G5** | Phenomenological Discrepancy | Detects numerical truncation errors and mesh singularity artifacts misattributed to physical mechanisms. | Active |
| **G6** | Kinematic Consistency | Detects contradictions between kinematic assumptions (e.g. plane stress vs. plane strain). | Active |
| **G7** | Scope & Regime Boundary | Audits reporting of applicability limits (small-scale yielding, linear elasticity thresholds). | Active |

---

## 4. Current Verification Scope & Known Limits

- **Test Suite**: 101 tests pass using 100% offline mocked fixtures to ensure fast, deterministic regression without consuming API quotas.
- **External Network Access**: Live queries to Crossref, OpenAlex, arXiv, and Semantic Scholar require active network connectivity and are subject to respective provider rate limits (documented in `docs/provider-policy.md`).
- **Mathematical Scope**: Positive-definiteness verification is currently implemented for linear elasticity with minor and major symmetries in Voigt notation.
