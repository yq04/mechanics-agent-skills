# Solid Mechanics Evidence & Formula Extraction Guidelines

## 1. Scope & Objective
This document outlines standard protocol for extracting verified mechanical equations, constitutive parameters, boundary conditions, and benchmark data from academic literature in solid mechanics, elasticity, and fracture mechanics.

## 2. Constitutive Properties & Tensors
1. **Linear Isotropic Elasticity**:
   - Young's modulus E, Poisson's ratio \nu, Shear modulus G = \mu = \frac{E}{2(1+\nu)}.
2. **Transversely Isotropic (TI) Elasticity**:
   - 5 independent stiffness constants: c_{11}, c_{12}, c_{13}, c_{33}, c_{44} (with c_{66} = (c_{11}-c_{12})/2).
   - Polarity axis: Typically aligned with the z-axis (x_3).
   - Distinct roots of characteristic equation: s_1, s_2 or complex conjugates.
3. **General Orthotropic & Piezoelectric Media**:
   - 9 orthotropic moduli: E_1, E_2, E_3, \nu_{12}, \nu_{23}, \nu_{13}, G_{12}, G_{23}, G_{13}.
   - Coupled piezoelectric tensors: e_{ijk}, dielectric permittivity \kappa_{ij}.

## 3. Defect Geometry & Boundary Conditions
1. **Penny-Shaped Cracks**:
   - Planar circular disk of radius a in plane z = 0.
   - Boundary conditions on crack face (r <= a):
     - Uniform tension at infinity: \sigma_{zz}^{\infty} = \sigma_0, crack faces traction-free \sigma_{zz} = 0.
     - Equivalent pressurized crack: internal pressure p(r) = \sigma_0.
2. **Elliptical Cracks**:
   - Semi-major axis a, semi-minor axis b (x^2/a^2 + y^2/b^2 <= 1).
   - Complete elliptic integrals of the first and second kind: K(k) and E(k) where k^2 = 1 - b^2/a^2.
3. **Interacting & Multi-Crack Configurations**:
   - Coplanar cracks: distance between centers l or ligament d = l - 2a.
   - Parallel non-coplanar cracks: vertical spacing h, horizontal offset s.

## 4. Potential Representations & Methods
1. **Fabrikant Potential Representation**:
   - Elementary potential F(x,y,z) reducing boundary value problems of penny-shaped defects in TI media to exact algebraic expressions.
2. **Papkovich-Neuber & Boussinesq Potentials**:
   - Harmonic scalar and vector potentials for 3D isotropic elasticity: u = B - \frac{1}{4(1-\nu)} \nabla(r \cdot B + B_0).
3. **Muskhelishvili Complex Potentials**:
   - Analytic functions \Phi(z), \Psi(z) for 2D plane strain / plane stress.
4. **Stroh Formalism**:
   - Sextic eigenvalue formulation for general anisotropic elasticity: N \xi = p \xi.

## 5. Stress Intensity Factors & Field Asymptotics
1. **Stress Intensity Factors (SIF)**:
   - Mode I (Opening): K_I = \lim_{r \to a^+} \sqrt{2\pi (r-a)} \sigma_{zz}(r, 0).
   - Baseline isolated penny crack under uniform tension \sigma_0: K_0 = \frac{2}{\pi} \sigma_0 \sqrt{\pi a}.
2. **Crack Opening Displacement (COD)**:
   - w(r) = u_z(r, 0^+) - u_z(r, 0^-).
   - Baseline isolated penny crack: w_0(r) = \frac{4(1-\nu^2)}{\pi E} \sigma_0 \sqrt{a^2 - r^2}.
3. **Benchmark Validation**:
   - Normalized SIF ratios: \gamma = K_I / K_0.
   - Canonical Collins 14 cases for two parallel penny-shaped cracks.
