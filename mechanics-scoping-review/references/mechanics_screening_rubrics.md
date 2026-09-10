# Mechanics Screening Rubrics & Scoring Criteria

## 1. Multi-Dimensional Mechanical Evaluation Schema

When screening scientific papers for solid mechanics and fracture mechanics topics, evaluations must strictly evaluate five fundamental engineering dimensions:

| Dimension | Target Scope (High Score) | Acceptable / Secondary | Excluded Scope (Zero Score) |
|---|---|---|---|
| **Constitutive Medium** | Transversely Isotropic (TI), Piezoelectric/Multiferroic TI, Orthotropic | Purely isotropic elasticity | Non-elastic fluids, granular discrete element, biological soft tissue |
| **Defect Geometry** | Coplanar penny-shaped, non-coplanar parallel cracks, elliptical cracks | 2D line cracks, single crack | Micro-void cavitation, bulk plastic void growth |
| **Analytical Method** | Fabrikant potential theory, Boussinesq-Papkovich potentials, Hankel transforms | Dual integral equations, Fredholm integral equations | Pure black-box finite element without analytical comparison |
| **Interaction Theory** | Kachanov self-consistent traction method, polynomial expansion, Fourier/wavelet | Point-force approximations, dipole expansion | Empirical phenomenological damage mechanics |
| **Output Quantities** | Full-field sigma/epsilon/u, closed-form COD w(r), SIF K_I/K_II/K_III, interaction matrix | Only global SIF without displacement fields | Experimental acoustic emission signals only |

## 2. Standard Scoring Scale (0 - 10 Points)

### Score 9 - 10: Critical Benchmark / Exact Foundation
- Directly treats multiple interacting cracks in anisotropic / TI media.
- Derives closed-form elementary potentials or explicit self-consistent transmission matrices.
- Provides exact mathematical proofs or canonical benchmark numerical tables (e.g. Collins 14 cases, SIF ratios).

### Score 7 - 8: Highly Relevant / Transferable Methodology
- Solves single crack under arbitrary asymmetric loading in TI medium (elementary potential available).
- Formulates higher-order polynomial or asymptotic Kachanov corrections in isotropic media with transferability to TI.
- Derives exact interaction energy or reciprocal theorem formulations for 3D defects.

### Score 4 - 6: Background / Contextual Reference
- Numerical studies (XFEM, BEM, peridynamics) of interacting penny-shaped cracks.
- Macro-homogenization of cracked solids without edge-stress singularities.
- Purely isotropic 2D crack interaction papers providing qualitative interaction physics.

### Score 0 - 3: Excluded
- Biomedical bone fracture or clinical orthopedic implant studies.
- Fluid mechanics cavitation or hydraulic fracturing without analytical crack-tip mechanics.
- Papers lacking mathematical derivations, governing equations, or theoretical mechanics relevance.