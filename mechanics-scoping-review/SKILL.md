---
name: mechanics-scoping-review
description: Rigorous PRISMA-ScR systematic and scoping literature review orchestration for Solid Mechanics, Fracture Mechanics, and Elasticity. Replaces biomedical PubMed APIs with engineering & mathematical backends (Crossref, OpenAlex, arXiv, Semantic Scholar), anchors records via canonical DOI, provides 5D mechanics screening rubrics (constitutive symmetry, defect geometry, potential theory, interaction models, output fields), multi-hop citation snowballing with Main Path Analysis (SPC), Mermaid network genealogies, evidence synthesis matrices, and PRISMA flowcharts. Use when conducting scoping reviews, surveying fracture mechanics literature, benchmarking analytical methods, or analyzing academic citation lineages.
metadata:
  version: "3.0.0"
  domain: "Solid Mechanics / Fracture Mechanics / Applied Mathematics"
  framework: "PRISMA-ScR Protocol"
---

# Mechanics Scoping Review: Systematic Literature Workflow

Production-grade scoping and systematic review pipeline engineered specifically for theoretical and computational solid mechanics.

## 1. Core Engineering Workflow
1. **Multi-Source DOI-Anchored Retrieval**: Queries Crossref, OpenAlex, arXiv, and Semantic Scholar with mechanics taxonomy expansion.
2. **5-Dimensional Screening Rubric**: Evaluates Constitutive Symmetry (Isotropic to Anisotropic/TI), Defect Geometry (penny-shaped, coplanar, parallel), Analytical Method (potentials, dual integrals, BEM), Interaction Theory (Kachanov, superposition), and Output Fields (SIF, COD, T-stress, $J$-integral). Scores 0-10 with transparent exclusion logs.
3. **Citation Snowballing & Main Path Analysis (SPC)**: Backward (references) and forward (citations) traversal, Search Path Count algorithmic backbone extraction, and publication-ready Mermaid citation flowcharts.
4. **Evidence Synthesis & PRISMA Reporting**: Generates standard PRISMA-ScR flowcharts in Mermaid, comprehensive Markdown Evidence Synthesis Matrices, and draft review sections with clean BibTeX references.

## 2. Quick CLI Usage

### End-to-End Scoping Review
```powershell
# Execute complete PRISMA-ScR review with taxonomy expansion, screening, BibTeX & synthesis
mechanics-review "interacting penny-shaped cracks in transversely isotropic media" --expand --output-dir review_artifacts
```

### Targeted Search, Citations & Extraction
```powershell
# Search literature across Crossref, OpenAlex, and arXiv with query expansion
mechanics-search "transversely isotropic crack interaction" --expand --format markdown

# Multi-hop citation snowballing with Mermaid export
mechanics-citations "10.1016/0020-7683(89)90001-X" --limit 20 --mermaid citation_tree.mmd

# Check Open Access PDF availability
mechanics-oa "10.1016/0020-7683(89)90001-X"
```

## 3. Five-Dimensional Mechanics Rubric (0 - 10)

| Dimension | Target Scope (High: 2 pts) | Contextual (1 pt) | Excluded (0 pts) |
|---|---|---|---|
| **Constitutive** | Transversely Isotropic (TI), Orthotropic, Anisotropic, Piezoelectric | Isotropic linear elasticity | Biological tissue, orthopedic implants, fluid cavitation |
| **Geometry** | Interacting cracks (coplanar, parallel non-coplanar), penny-shaped, elliptical | 2D single crack, generic notch | Macro-void cavitation without crack geometry |
| **Method** | Potential theory (Fabrikant, Papkovich-Neuber, Muskhelishvili), dual integrals | Numerical BEM/XFEM with benchmark | Black-box commercial FEA without analytical equations |
| **Interaction** | Kachanov self-consistent traction method, transmission matrices | Far-field or dipole approximations | Purely empirical phenomenological damage |
| **Fields** | Stress Intensity Factors ($K_I, K_{II}, K_{III}$), COD ($w(r)$), $J$-integral | Global stress concentration | Purely qualitative experimental acoustics |

- **Included / Priority**: Score $\ge 7$
- **Contextual / Background**: Score 4 - 6
- **Excluded**: Score 0 - 3 (with explicit rationale logged)

## 4. References & Protocols
- [scoping_review_protocol.md](references/scoping_review_protocol.md): Full PRISMA-ScR phase transitions.
- [mechanics_screening_rubrics.md](references/mechanics_screening_rubrics.md): Granular scoring criteria.
- [subagent_orchestration_guide.md](references/subagent_orchestration_guide.md): Parallel batch execution guide.
- [database_api_strategies.md](references/database_api_strategies.md): API rate limits and polite pool headers.
