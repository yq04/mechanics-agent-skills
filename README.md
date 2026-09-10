# Mechanics Agent Skills: PRISMA-ScR Systematic Review & Knowledge Graph Suite

A production-grade agent skills ecosystem engineered specifically for researchers in **Solid Mechanics, Fracture Mechanics, Elasticity, and Applied Mathematics**.

## Overview

General-purpose literature tools often hard-code biomedical endpoints (PubMed/PMID) and lack domain criteria for continuum and fracture mechanics. This suite provides two standardized skills:

1. **`mechanics-scoping-review`**: PRISMA-ScR literature review orchestration customized for mechanics.
   - Multi-source search: Crossref, OpenAlex, arXiv, and Semantic Scholar.
   - DOI-anchored literature management.
   - Mechanics-specific screening rubric (Constitutive symmetry, defect geometry, potential theory, SIF/COD fields).
   - Parallel subagent-driven batch screening.
   - Citation network backward and forward snowballing.
   - Legal Open Access PDF discovery via Unpaywall.

2. **`openalex-database`**: OpenAlex 250M+ scholarly knowledge graph querying tools with polite pool access.

## Structure

```text
mechanics-agent-skills/
|-- mechanics-scoping-review/
|   |-- SKILL.md
|   |-- references/
|   |   |-- scoping_review_protocol.md
|   |   |-- mechanics_screening_rubrics.md
|   |   |-- subagent_orchestration_guide.md
|   |   `-- database_api_strategies.md
|   `-- scripts/
|       |-- search_mechanics_papers.py
|       |-- traverse_mechanics_citations.py
|       `-- find_oa_pdf.py
`-- openalex-database/
    |-- SKILL.md
    |-- references/
    `-- scripts/
```

## Quick CLI Usage

```bash
# Search mechanics papers across Crossref, OpenAlex, arXiv
python mechanics-scoping-review/scripts/search_mechanics_papers.py "anisotropic elasticity crack problem" --limit 10

# Traverse citation graph
python mechanics-scoping-review/scripts/traverse_mechanics_citations.py "10.1016/j.engfracmech.2020.107000"

# Find open access full text
python mechanics-scoping-review/scripts/find_oa_pdf.py "10.1016/j.engfracmech.2020.107000"
```

## License

Licensed under the MIT License.
