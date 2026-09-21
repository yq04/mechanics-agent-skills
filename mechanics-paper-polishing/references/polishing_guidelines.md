# Mechanics Manuscript Polishing & Style Guidelines

## 1. Mathematical Preservation Principles
In solid and fracture mechanics papers, mathematical equations embody fundamental physics and boundary value problems.
No automated language model is authorized to change mathematical symbols, subscript notations, indices, or factors without explicit derivation.

### Protected Elements
- Display math environments: `equation`, `align`, `gather`, `multline`.
- Inline math delimiters: `$...$`, `\(...\)`.
- Citation anchors: `\cite{...}`, `[@bibkey]`.
- References & labels: `\ref{...}`, `\eqref{...}`, `\label{...}`.
- Numerical quantities with units: `120 GPa`, `15.4 MPa m^{1/2}`.

---

## 2. High-Risk Notation Ambiguities

### COD vs Single-Side Displacement $w$
- General Definition: Crack opening displacement is the displacement discontinuity vector jump across crack faces:
  $$[u] = u^+ - u^-$$
- Symmetric Mode I: For a crack symmetric about the crack plane ($y=0$), $u_y^+ = w$ and $u_y^- = -w$, so:
  $$\mathrm{COD} = 2w$$
- Common Pitfall: Equating $\mathrm{COD} = w$ without specifying whether $w$ is total opening or half-opening.

### SIF Normalizations
- Irwin Definition:
  $$K_I = \lim_{r \to 0} \sigma_{yy} \sqrt{2\pi r}$$
- Sneddon / Barenblatt Definition:
  $$k_I = \lim_{r \to 0} \sigma_{yy} \sqrt{2 r} = \frac{K_I}{\sqrt{\pi}}$$
- Pitfall: SIF ratio discrepancies of $\sqrt{\pi} \approx 1.772$ between US and Russian/European elasticity literature.

### Engineering Shear vs Tensorial Shear
- Tensorial shear strain: $\varepsilon_{xy} = \frac{1}{2}\left(\frac{\partial u_x}{\partial y} + \frac{\partial u_y}{\partial x}\right)$
- Engineering shear strain: $\gamma_{xy} = 2\varepsilon_{xy}$

---

## 3. Recommended Phrasing (AI Fluff vs Physical Rigor)

| Cliché to Eliminate | Preferred Mechanics Phrasing |
|---|---|
| This work delves into the crack analysis... | We formulate the singular integral equations governing... |
| Serves as a testament to the crucial interplay... | Demonstrates the coupling between microstructure and macroscopic fracture resistance... |
| Underscores the pivotal role of... | Indicates that elastic mismatch governs... |
| Fosters enhanced fracture toughness... | Induces crack tip stress shielding, increasing apparent toughness... |
| A rich tapestry of stress fields... | Complex multi-defect stress interaction... |
| An exact solution from FEM... | A converged numerical approximation obtained via finite element analysis... |
