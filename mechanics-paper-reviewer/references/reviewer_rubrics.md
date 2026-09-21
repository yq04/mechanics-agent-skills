# Mechanics Peer Review Rubrics & Five-Dimensional Soundness Matrix

## 1. Dimensional Evaluation Rubrics

### Dimension 1: Governing Equations Completeness
- **Supported**: Problem statement specifies global coordinate system (e.g. Cartesian, polar), states balance of momentum ($\nabla \cdot \sigma + b = \rho \ddot{u}$), kinematics ($\varepsilon = \frac{1}{2}(\nabla u + \nabla u^T)$), and governing PDE system or potential representation (Airy, Papkovich-Neuber, Stroh).
- **Concern**: Missing coordinate axes, undefined differential operators, unstated field equations, or unclosed systems.

### Dimension 2: Constitutive, Symmetry & Admissibility
- **Supported**: Explicit stress-strain relations with clear material symmetry classification (isotropic, transversely isotropic, orthotropic) and positive-definite stiffness tensor ($C_{ijkl} > 0$).
- **Concern**: Undefined elastic constants, unstated symmetry class, thermodynamic instability, or applying isotropic bounds to anisotropic materials.

### Dimension 3: Boundary & Interface Conditions
- **Supported**: Complete specification of Dirichlet (displacement) and Neumann (traction) boundary conditions. Crack surfaces clearly designated as traction-free ($\sigma \cdot n = 0$), pressurized, or in contact. Interface jump conditions ($[u]$, $[\sigma \cdot n]$) stated.
- **Concern**: Incomplete outer boundary conditions, ambiguous crack-face loading, or unspecified contact conditions.

### Dimension 4: Validation, Convergence & Reproducibility
- **Supported**: Quantitative comparison against independent canonical analytical benchmarks (Westergaard, Sneddon, Tada-Paris-Irwin) and systematic grid/mesh convergence study demonstrating asymptotic independence.
- **Concern**: Validation only against the author's own simulation code, missing convergence studies, or absent error norms.

### Dimension 5: Physical Interpretation & Mechanism
- **Supported**: Observed trends (e.g. SIF reduction, crack deflection, toughening) attributed to clear mechanics mechanisms (elastic mismatch, stress shielding, microcrack interaction, energy dissipation).
- **Concern**: Purely descriptive narrative of curve shapes, or misinterpreting numerical mesh singularities as "novel physical discoveries".
