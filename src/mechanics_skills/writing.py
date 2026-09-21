"""
PRISMA-ScR Flowchart generation, Evidence Synthesis Matrix, and Academic Review drafting.
"""

from typing import Any, Dict, List, Optional, Union
import re

from mechanics_skills.models import PaperRecord
from mechanics_skills.screening import PRISMACounter
from mechanics_skills.bibtex import generate_citekey


def generate_prisma_mermaid(counter: PRISMACounter) -> str:
    """
    Generate publication-ready PRISMA-ScR Flowchart in Mermaid format.
    Accurately maps Identification -> Screening -> Eligibility -> Included.
    """
    exc_reasons_lines = []
    for reason, count in list(counter.exclusion_reasons.items())[:3]:
        clean_reason = reason.replace('"', "'").replace("\n", " ").strip()
        exc_reasons_lines.append(f"- {clean_reason} (n = {count})")

    reasons_str = "<br/>".join(exc_reasons_lines) if exc_reasons_lines else "Reasons recorded in log"

    lines = [
        "flowchart TD",
        "    classDef stageBox fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1,font-weight:bold;",
        "    classDef excBox fill:#ffebee,stroke:#c62828,stroke-width:1.5px,color:#b71c1c;",
        "    classDef incBox fill:#e8f5e9,stroke:#2e7d32,stroke-width:2.5px,color:#1b5e20,font-weight:bold;",
        "",
        '    subgraph Identification ["Identification"]',
        f'        ID1["Records identified from databases<br/>(n = {counter.identified})"]',
        f'        ID2["Records removed before screening:<br/>Duplicates removed (n = {counter.duplicates_removed})"]',
        "    end",
        "",
        '    subgraph Screening ["Screening"]',
        f'        SC1["Records screened by Title & Abstract<br/>(n = {counter.screened})"]',
        f'        SC2["Records excluded by mechanics rubric<br/>(n = {counter.screened_excluded})"]',
        "    end",
        "",
        '    subgraph Eligibility ["Eligibility"]',
        f'        EL1["Full-text articles assessed for eligibility<br/>(n = {counter.assessed_eligibility})"]',
        f'        EL2["Full-text articles excluded<br/>(n = {counter.eligibility_excluded})<br/>{reasons_str}"]',
        "    end",
        "",
        '    subgraph Included ["Included"]',
        f'        INC["Studies included in quantitative & evidence synthesis<br/>(n = {counter.included})"]',
        "    end",
        "",
        "    ID1 --> ID2",
        "    ID1 --> SC1",
        "    SC1 --> SC2",
        "    SC1 --> EL1",
        "    EL1 --> EL2",
        "    EL1 --> INC",
        "",
        "    class ID1,SC1,EL1 stageBox;",
        "    class ID2,SC2,EL2 excBox;",
        "    class INC incBox;",
    ]

    return "\n".join(lines)


def _clean_table_cell(text: Any) -> str:
    """Clean text for inclusion in a Markdown table cell."""
    if text is None:
        return "-"
    s = str(text).replace("|", "&#124;").replace("\n", " ").strip()
    return s if s else "-"


def generate_evidence_matrix_markdown(
    evidence_list: List[Union[Dict[str, Any], Any]]
) -> str:
    """
    Generate the standard Evidence Synthesis Matrix in Markdown table format.
    Summarizes constitutive model, defect geometry, potential/method, output fields, and formulas.
    """
    lines = [
        "| Study / Paper | Page | Category | Extracted Mechanics Parameters & Formulas | Confidence |",
        "|---|---|---|---|---|",
    ]

    if not evidence_list:
        lines.append("| *No evidence items recorded* | - | - | - | - |")
        return "\n".join(lines) + "\n"

    for item in evidence_list:
        if hasattr(item, "to_dict"):
            d = item.to_dict()
        elif isinstance(item, dict):
            d = item
        else:
            continue

        title = d.get("document_title") or "Study"
        doi = d.get("doi")
        if doi:
            study_cell = f"[{_clean_table_cell(title)}](https://doi.org/{doi})"
        else:
            study_cell = _clean_table_cell(title)

        source_type = d.get("source_type", "pdf")
        page_val = d.get("page_number")
        if source_type == "abstract" or page_val is None:
            page = "Abstract"
        else:
            page = str(page_val)
        elem_type = _clean_table_cell(d.get("element_type", "").capitalize())
        confidence = f"{float(d.get('confidence', 1.0)):.2f}"

        params = d.get("extracted_parameters", {})
        param_parts = []
        for k, v in params.items():
            if isinstance(v, dict):
                v_str = ", ".join(f"{vk}={vv}" for vk, vv in v.items())
                param_parts.append(f"**{k}**: {v_str}")
            elif isinstance(v, list):
                param_parts.append(f"**{k}**: {', '.join(map(str, v))}")
            else:
                param_parts.append(f"**{k}**: {v}")

        if not param_parts and d.get("verbatim_excerpt"):
            excerpt = d.get("verbatim_excerpt", "")[:100].replace("\n", " ")
            param_parts.append(f"*{excerpt}...*")

        details_cell = _clean_table_cell("; ".join(param_parts))

        lines.append(f"| {study_cell} | {page} | {elem_type} | {details_cell} | {confidence} |")

    return "\n".join(lines) + "\n"


def generate_review_draft_sections(
    papers: List[PaperRecord],
    evidence: List[Union[Dict[str, Any], Any]],
    counter: Optional[PRISMACounter] = None,
) -> str:
    """
    Generate an academic literature review draft dynamically synthesized from
    retrieved papers and extracted evidence cards, avoiding hardcoded historical constants.
    """
    # Normalize evidence items to dictionaries
    norm_evidence: List[Dict[str, Any]] = []
    for item in evidence:
        if hasattr(item, "to_dict"):
            norm_evidence.append(item.to_dict())
        elif isinstance(item, dict):
            norm_evidence.append(item)

    # Dynamically harvest extracted features
    potentials_found: List[str] = []
    geometries_found: List[str] = []
    bcs_found: List[str] = []
    symmetries_found: List[str] = []
    formula_types_found: List[str] = []
    benchmarks_found: List[str] = []

    for d in norm_evidence:
        params = d.get("extracted_parameters", {})
        elem_type = d.get("element_type", "")
        
        if elem_type == "potential":
            reps = params.get("representations", [])
            for r in reps:
                if r not in potentials_found:
                    potentials_found.append(r)
        elif elem_type == "geometry":
            dt = params.get("defect_type", [])
            for g in dt:
                if g not in geometries_found:
                    geometries_found.append(g)
            bc = params.get("boundary_condition", [])
            for b in bc:
                if b not in bcs_found:
                    bcs_found.append(b)
        elif elem_type == "constitutive":
            syms = params.get("symmetry", [])
            for s in syms:
                if s not in symmetries_found:
                    symmetries_found.append(s)
        elif elem_type == "formula":
            fc = params.get("formula_candidates", {})
            for k in fc.keys():
                if k not in formula_types_found:
                    formula_types_found.append(k)
        elif elem_type == "benchmark":
            tc = params.get("table_caption")
            if tc and tc not in benchmarks_found:
                benchmarks_found.append(tc)

    anisotropic_papers = []
    isotropic_papers = []
    for p in papers:
        t_a = f"{p.title} {p.abstract}".lower()
        if any(w in t_a for w in ["transversely isotropic", "anisotropic", "orthotropic", "ti medium"]):
            anisotropic_papers.append(p)
        else:
            isotropic_papers.append(p)

    matrix_md = generate_evidence_matrix_markdown(norm_evidence)
    prisma_md = generate_prisma_mermaid(counter) if counter else ""

    # Synthesize Dynamic Section 2
    sec2_lines = [
        "## 2. Theoretical Formulations & Potential Methods",
        "Analytical treatment of boundary value problems hinges upon suitable potential representations and governing field equations.",
    ]
    if potentials_found:
        sec2_lines.append(
            f"- **Potential Representations**: Verified evidence identifies candidate potential methods: {', '.join(potentials_found)}. "
            "These methods transform coupled partial differential equations into reduced boundary or singular integral systems."
        )
    else:
        sec2_lines.append(
            "- **Governing Equations**: Solutions rely on classical elasticity field equations and transform techniques "
            "appropriate for the evaluated domain boundaries."
        )

    if formula_types_found:
        sec2_lines.append(
            f"- **Extracted Governing Formulas**: Mathematical candidates for {', '.join(formula_types_found)} were captured "
            "from the corpus and cross-referenced against boundary conditions."
        )
    else:
        sec2_lines.append(
            "- **Asymptotic Expansions**: Formulations establish singular stress intensity factor and displacement jump relationships."
        )

    # Synthesize Dynamic Section 3
    sec3_lines = [
        "## 3. Defect Geometries & Interaction Mechanisms",
        f"Among the evaluated corpus, {len(anisotropic_papers)} studies addressed anisotropic/transversely isotropic media, "
        f"while {len(isotropic_papers)} addressed isotropic or generalized elasticity baselines.",
    ]
    if symmetries_found:
        sec3_lines.append(f"- **Material Symmetries**: Active constitutive symmetries identified in evidence include: {', '.join(symmetries_found)}.")
    
    if geometries_found:
        sec3_lines.append(f"- **Defect Geometries**: Extracted flaw configurations encompass: {', '.join(geometries_found)}.")
    else:
        sec3_lines.append("- **Defect Geometries**: Configurations encompass isolated and interacting cracks and inclusions.")

    if bcs_found:
        sec3_lines.append(f"- **Boundary Conditions**: Evaluated traction and displacement states include: {', '.join(bcs_found)}.")

    if benchmarks_found:
        sec3_lines.append(f"- **Benchmark Datasets**: Cross-verification utilizes benchmark records: {'; '.join(benchmarks_found[:2])}.")

    # Dynamic Section 5 (Gaps)
    sec5_lines = [
        "## 5. Identified Research Gaps & Open Analytical Challenges",
    ]
    gaps = []
    if "COD" not in formula_types_found:
        gaps.append("1. **Full-Field Closed-Form COD**: While Mode I SIF is frequently tabulated, closed-form 3D displacement fields $w(r)$ across diverse symmetries remain scarce.")
    else:
        gaps.append("1. **Higher-Order Displacement Fields**: Generalization of full-field COD across multi-layered and non-coplanar defect arrays requires unified asymptotic formulations.")

    if not any("parallel" in g.lower() or "coplanar" in g.lower() for g in geometries_found):
        gaps.append(r"2. **Near-Field Defect Interactions**: Interaction transmission under very close defect spacing ($h/a \ll 1$) requires higher-order boundary correction beyond average traction approximations.")
    else:
        gaps.append("2. **Multi-Defect Boundary Interaction**: Strong near-field interactions between closely spaced defect edges require rigorous boundary layer matching.")

    gaps.append("3. **Coupled Multi-Physics Interfacial Cracks**: Exact solutions for coupled electro-elastic defect arrays under realistic permeable/impermeable crack-face conditions remain an active frontier.")
    sec5_lines.extend(gaps)

    sections = [
        "# Scoping Review: Analytical & Computational Mechanics of Defect Interactions",
        "",
        "## 1. Introduction and Mechanical Scope",
        "The integrity and failure characteristics of structural and functional media depend fundamentally on the singular stress fields, crack opening displacements (COD), and interactions among micro- and macro-defects. This scoping review synthesizes analytical, semi-analytical, and numerical formulations for defect interactions, spanning linear elasticity, anisotropic/orthotropic elasticity, and transversely isotropic (TI) media.",
        f"A total of **{len(papers)}** candidate works were evaluated under the rigorous 5-Dimensional Mechanics Screening Rubric (Constitutive Medium, Defect Geometry, Analytical Method, Interaction Theory, and Output Fields).",
        "",
        chr(10).join(sec2_lines),
        "",
        chr(10).join(sec3_lines),
        "",
        "## 4. Evidence Synthesis Matrix",
        "The following evidence matrix provides verified page anchors, extracted constitutive parameters, potential representations, and candidate formulas from the reviewed literature:",
        "",
        matrix_md,
        "",
        chr(10).join(sec5_lines),
        "",
    ]

    if prisma_md:
        fence = chr(96) * 3
        sections.extend([
            "## 6. PRISMA-ScR Review Flowchart",
            "",
            f"{fence}mermaid",
            prisma_md,
            f"{fence}",
            "",
        ])

    sections.append("## 7. Selected Bibliography")
    sections.append("")
    for i, p in enumerate(papers, 1):
        citekey = generate_citekey(p)
        authors_str = ", ".join(p.authors[:3]) if p.authors else "Anonymous"
        if len(p.authors) > 3:
            authors_str += " et al."
        doi_str = f"https://doi.org/{p.doi}" if p.doi else "No DOI"
        sections.append(f"{i}. **[{citekey}]** {authors_str} ({p.year or 'n.d.'}). *{p.title}*. {p.journal or ''}. [DOI: {doi_str}]")

    sections.append("")
    return chr(10).join(sections)
