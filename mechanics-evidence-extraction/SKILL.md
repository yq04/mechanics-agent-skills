---
name: mechanics-evidence-extraction
description: Universal evidence, constitutive tensor, potential representation, and candidate formula extractor for Solid Mechanics, Fracture Mechanics, and Elasticity literature. Extracts verified page-anchored evidence cards from PDF or text, capturing elastic moduli, defect geometries, boundary conditions, Fabrikant/Papkovich potentials, SIF and COD formulas, and benchmark tables. Use when reading full-text mechanics papers, extracting constitutive data, compiling evidence synthesis matrices, or auditing mathematical equations.
metadata:
  version: "3.0.0"
  domain: "Solid Mechanics / Fracture Mechanics / Applied Mathematics"
---

# Mechanics Evidence & Formula Extraction

Automated, page-anchored evidence extraction for solid mechanics and fracture mechanics papers.
Parses PDFs (via PyMuPDF) or plain-text preprints into structured, audit-ready evidence cards.

## 1. When to Use
- Extracting constitutive properties ($E, \nu, G$, stiffness matrix $c_{ij}$, compliance $s_{ij}$, piezoelectric $e_{ij}$).
- Identifying defect geometries (penny-shaped cracks, elliptical cracks, coplanar/parallel non-coplanar flaws, inclusions).
- Extracting analytical potential formulations (Fabrikant potentials, Papkovich-Neuber, Muskhelishvili, Stroh).
- Locating candidate governing equations and closed-form solutions (SIF $K_I, K_{II}, K_{III}$, COD $w(r)$, $J$-integral).
- Compiling evidence synthesis matrices and benchmark comparisons across literature.

## 2. Quick CLI Usage

### Direct CLI Commands
```powershell
# Extract evidence from PDF into structured JSON and Markdown synthesis matrix
mechanics-extract paper.pdf --output evidence.json --markdown matrix.md

# Extract evidence from plain-text preprint or note
mechanics-extract preprint.txt --title "Fabrikant 1989" --doi "10.1016/sample" --format json

# Or use unified CLI
mechanics-skills extract paper.pdf --format markdown
```

### Python API
```python
from mechanics_skills.extraction import extract_evidence_from_pdf, extract_evidence_from_text

# From PDF
cards = extract_evidence_from_pdf("paper.pdf", document_title="Collins 1963", doi="10.1098/rspa.1963.0163")

# From Text
cards = extract_evidence_from_text(paper_text, document_title="Fabrikant 1989", page_number=5)

for card in cards:
    print(f"[{card.element_type}] Page {card.page_number} -> {card.extracted_parameters}")
```

## 3. Extracted Evidence Categories

| Element Type | Target Content |
|---|---|
| **constitutive** | Elastic moduli ($E, \nu, G$), TI/orthotropic stiffness ($c_{11}, c_{33}, c_{44}$), piezoelectric coefficients ($e_{ij}$). |
| **geometry** | Defect geometry (radius $a$, axes $a, b$, spacing $h, d$), boundary conditions (uniform tension, internal pressure, shear). |
| **potential** | Analytical representation (Fabrikant elementary potentials, Papkovich-Neuber, Muskhelishvili, Stroh). |
| **formula** | Candidate expressions for SIF ($K_I = \dots$), COD ($w(r) = \dots$), energy release rates ($G, J$). |
| **benchmark** | Numerical benchmark tables, normalized interaction factors ($K_I / K_0$), canonical Collins cases. |

## 4. Deep Reference Guidelines
- Refer to [extraction_guidelines.md](references/extraction_guidelines.md) for full mechanics tensor definitions, SIF normalization baselines, and benchmark reference cases.
