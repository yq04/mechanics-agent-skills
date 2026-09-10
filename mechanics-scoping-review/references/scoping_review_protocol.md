# PRISMA-ScR Protocol for Solid Mechanics & Fracture Mechanics

## 1. Overview and Core Philosophy

This protocol establishes the standardized, reproducible methodology for scoping and systematic reviews in solid mechanics, anisotropic elasticity, and fracture mechanics, adapted from the PRISMA-ScR (Preferred Reporting Items for Systematic reviews and Meta-Analyses extension for Scoping Reviews) statement.

In rigorous theoretical mechanics, literature review is not passive reading; it is a systematic audit of analytical solutions, constitutive assumptions, boundary conditions, interaction models, and numerical benchmarks to establish definitive novelty and identify research gaps.

## 2. Six-Phase Review Workflow

### Phase 1: Review Question Formulation & Screening Rubric Design
- Formulate precise mechanical scope: (1) Constitutive symmetry, (2) Crack geometry and spatial arrangement, (3) Boundary condition and loading mode, (4) Theoretical/numerical solution technique, (5) Target mechanical outputs.
- Establish explicit Inclusion Criteria (IC) and Exclusion Criteria (EC).
- Calibrate scoring rubric (0 to 10 scale) on a test set of 5-10 known papers.

### Phase 2: Multi-Source Literature Retrieval
- Query across engineering and applied mathematical databases: Crossref (authoritative DOI repository), OpenAlex (240M+ graph with polite pool), arXiv (preprints in mathematical physics/mechanics), and Semantic Scholar.
- Anchor every record by canonical lowercase DOI. Deduplicate records across title hashes and DOIs.
- Preserve structured JSON record with title, authors, year, journal, citations, abstract, and DOI.

### Phase 3: Two-Stage Paper Screening
- **Stage 1 (Title & Abstract Screening)**: Fast evaluation against the mechanics rubric. Grade papers from 0 to 10. Split into Priority (>=7), Reference (4-6), and Excluded (0-3).
- **Stage 2 (Full-Text Deep Dive)**: For Priority papers, inspect full text for explicit governing equations, potential representations, interaction matrices, and numerical tables.

### Phase 4: Parallel Subagent Execution (for batches >= 30 papers)
- When screening large sets, dispatch independent subagents for disjoint paper batches (10-20 papers per subagent).
- Subagents write batch evaluations into structured JSON logs.
- Main orchestrator consolidates results, performs quality audits, and eliminates inconsistencies.

### Phase 5: Citation Network Snowballing
- Identify foundational "seed papers" (e.g., Collins 1963, Fabrikant 1989, Kachanov 1987).
- **Backward Snowballing**: Extract historical references cited by seed papers to discover earlier analytical formulations.
- **Forward Snowballing**: Extract papers citing the seed work to capture modern generalizations, higher-order corrections, and experimental benchmarks.

### Phase 6: Synthesis and Evidence Matrix Reporting
- Synthesize findings into structured comparative tables covering:
  1. Constitutive class (Isotropic, TI, Orthotropic, Anisotropic)
  2. Crack arrangement (Single, Two coplanar, Periodic, Three-dimensional spatial)
  3. Method of solution (Potential theory, Dual integral equations, Kachanov self-consistent, Higher-order polynomial, BEM, FEM)
  4. Mechanical fields resolved (SIF K_I/K_II/K_III, COD w, stress tensor sigma, strain tensor epsilon, interaction energy)
  5. Exact benchmark validation data (e.g. Collins 14-case tables)
- Formulate definitive research gaps and novelty claims for the active dissertation topic.