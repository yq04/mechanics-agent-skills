---
name: mechanics-scoping-review
description: Rigorous PRISMA-ScR systematic and scoping literature review orchestration specifically customized for Solid Mechanics, Fracture Mechanics, and Elasticity. Replaces biomedical PubMed APIs with open mechanics engineering backends (Crossref, OpenAlex, arXiv, Semantic Scholar), anchors records via canonical DOI, provides mechanics-specific screening rubrics (constitutive symmetry, defect geometry, potential representations, SIF/COD fields), supports subagent-driven parallel batch screening, backward/forward citation snowballing, and evidence synthesis matrices.
when_to_use: When conducting systematic or scoping literature reviews in solid mechanics, elasticity, or fracture mechanics; when researching analytical/semi-analytical/numerical solutions for cracks, inclusions, or contact problems; when benchmarking mechanical interaction theories (BEM, FEM, analytical potentials); when establishing screening rubrics or traversing citation networks.
version: 2.1.0
metadata:
  domain: Solid Mechanics / Fracture Mechanics / Applied Mathematics
  framework: PRISMA-ScR Protocol
  backends: Crossref REST API, OpenAlex API, arXiv API, Unpaywall API
---

# Mechanics Scoping Review: Systematic Literature Workflow

## 1. Overview & Core Engineering Methodology

Theoretical solid mechanics and fracture mechanics require rigorous mathematical and physical auditing of literature. Standard superficial web searches frequently miss foundational exact solutions or confuse disparate constitutive models.

This skill implements a standardized **PRISMA-ScR workflow** engineered specifically for solid mechanics:
1. **DOI-Anchored Multi-Source Retrieval**: Queries Crossref (publisher metadata), OpenAlex (global scholarly graph), and arXiv (applied math preprints) with zero biomedical bias.
2. **Mechanics-Specific Screening Rubric**: Evaluates constitutive symmetry (anisotropic, isotropic), defect topology (planar cracks, inclusions, notches), theoretical formulation (potential theory, dual integral equations, boundary integral equations), and target mechanical fields (SIF, COD, stress tensor, strain energy).
3. **Two-Stage Screening & Parallel Subagent Delegation**: Supports high-throughput, context-isolated batch screening via subagents with consolidation checkpoints.
4. **Citation Network Snowballing**: Follows backward references and forward citations from seminal seed papers to map the entire theoretical lineage.
5. **Evidence Synthesis Matrix**: Produces comparative analytical-versus-numerical benchmark tables and establishes incontrovertible research gaps.

## 2. Directory Layout and Tool Ecosystem

```text
mechanics-scoping-review/
|-- SKILL.md                              # Main orchestration instructions (this file)
|-- references/
|   |-- scoping_review_protocol.md        # PRISMA-ScR protocol & phase transitions
|   |-- mechanics_screening_rubrics.md    # Solid mechanics evaluation criteria & scoring scale
|   |-- subagent_orchestration_guide.md   # Parallel delegation & JSON merge protocols
|   `-- database_api_strategies.md        # Multi-backend API fallback & rate limits
`-- scripts/
    |-- search_mechanics_papers.py        # CLI for Crossref + OpenAlex + arXiv search
    |-- traverse_mechanics_citations.py   # CLI for backward/forward citation snowballing
    `-- find_oa_pdf.py                    # CLI for Unpaywall & OpenAlex OA PDF retrieval
```

## 3. Step-by-Step Review Execution

### Step 1: Define Topic Scope & Calibrate Rubric
- Consult `references/mechanics_screening_rubrics.md` to establish the target parameters.
- Define explicit inclusion/exclusion criteria:
  - *Target Constitutive*: Linear elastic, anisotropic or isotropic media.
  - *Target Defect*: Discrete cracks, notches, or inclusions.
  - *Target Theory*: Analytical boundary value methods, integral transforms, or semi-analytical formulations.
  - *Exclusion*: Purely empirical observations, non-continuum fluid cavitation, biological soft tissues.

### Step 2: Multi-Source Literature Retrieval
Execute `search_mechanics_papers.py` with domain-optimized keywords:
```bash
python mechanics-scoping-review/scripts/search_mechanics_papers.py \
  "anisotropic elasticity crack problem analytical solution" \
  --limit 20 \
  --output literature_search.json \
  --markdown LITERATURE_SEARCH_TABLE.md
```

### Step 3: Screening & Evaluation
- For small paper sets (< 25 papers): Perform direct abstract evaluation using the 0-10 scoring rubric.
- For large paper sets (>= 25 papers): Follow `references/subagent_orchestration_guide.md` to partition into batches and dispatch parallel subagents.
- Partition results into:
  - **Priority Papers (Score >= 7)**: Selected for deep dive and citation snowballing.
  - **Background Papers (Score 4 - 6)**: Retained for contextual comparison.
  - **Excluded Papers (Score 0 - 3)**: Documented with explicit exclusion rationale.

### Step 4: Citation Network Snowballing
Take key seed papers and traverse the citation network:
```bash
python mechanics-scoping-review/scripts/traverse_mechanics_citations.py \
  "10.1016/j.engfracmech.2020.107000" \
  --limit 25 \
  --output citation_network.json
```

### Step 5: Full-Text Retrieval & Deep Dive Data Extraction
For priority papers, locate legal Open Access full texts:
```bash
python mechanics-scoping-review/scripts/find_oa_pdf.py "10.1016/j.engfracmech.2020.107000"
```
Extract governing formulas, displacement potentials, transmission coefficients, and benchmark validation tables.

### Step 6: Evidence Synthesis Matrix
Construct the definitive scoping review synthesis table in Markdown format:
| Reference | Medium | Defect Geometry | Analytical Method | Field Quantities | SIF Closed-Form? | Numerical Benchmarks | Evidence Level |
|---|---|---|---|---|---|---|---|
| Classical Study A | Isotropic | Coplanar defect array | Integral transforms | Displacements, Stresses | Yes (Exact) | Standard verification | Foundational (10/10) |
| Classical Study B | Anisotropic | 3D planar crack | Potential theory | Singular stress fields | Semi-analytical | Convergence verified | High (8/10) |
| Benchmark Study C | Layered medium | Interfacial defect | Boundary integral | Traction distribution | Numerical / BEM | Experimental match | Contextual (6/10) |
