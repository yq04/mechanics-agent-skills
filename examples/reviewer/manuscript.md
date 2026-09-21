# Asymptotic Stress Fields Near Collinear Cracks in Elastic Solids

## Abstract
This work investigates crack-tip stress fields in linear elastic media under mode I loading.
The apparent stress intensity factor is computed for normalized spacing $h/a$.

## 1. Introduction
Understanding defect interactions is essential in structural integrity assessment.
Previous analytical formulations by \cite{Westergaard1939} provided closed-form potentials for isolated cracks.
Here, we evaluate the shielding mechanism arising in interacting collinear crack arrays.

## 2. Governing Equations and Boundary Value Problem
We adopt a Cartesian coordinate system $(x, y)$ centered at the primary crack midpoint.
In the absence of body forces, the field equations are governed by Cauchy equilibrium:
\begin{equation}
\nabla \cdot \sigma = 0
\end{equation}
The material is modeled as linear isotropic with Young's modulus 70 GPa and Poisson's ratio 0.33.
The crack faces are assumed traction-free:
\begin{equation}
\sigma_{yy}(x, 0) = 0, \quad |x| < a
\end{equation}
At infinity, uniform tensile traction $\sigma_0 = 100\text{ MPa}$ is prescribed.

## 3. Benchmark Verification
Numerical results are compared against the Westergaard canonical solution for an isolated crack:
\begin{equation}
K_I = \sigma_0 \sqrt{\pi a}
\end{equation}
Agreement within 0.15% is achieved under systematic mesh refinement.

## 4. Physical Mechanism
Stress redistribution between neighboring crack tips induces apparent stress shielding, reducing the local stress intensity factor.
