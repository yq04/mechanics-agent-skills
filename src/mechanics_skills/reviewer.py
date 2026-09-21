"""
Simulated Mechanics Peer Review & Five-Dimensional Soundness Audit.
Phase 8 implementation for mechanics-agent-skills:
- Five-Dimensional Soundness Checklist (D1~D5)
- Journal profile heuristics (JMPS, IJSS, EFM, Acta Mech Sin, Generic)
- Comprehensive soundness audit: audit_scientific_soundness
- Structured Markdown peer review report generation: generate_review_report_markdown
- Revision comparison & resolution verification: compare_revision
- Review package preparation: prepare_review_package
"""

import dataclasses
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from mechanics_skills.integrity import Finding, ConventionRegistry


JOURNAL_PROFILES = {
    "jmps": {
        "journal_code": "jmps",
        "full_name": "Journal of the Mechanics and Physics of Solids",
        "focus_description": (
            "Foundational continuum mechanics, micromechanics, rigorous mathematical closures, "
            "analytical potentials, and deep physical mechanisms connecting microstructure to macroscopic response."
        ),
        "priority_dimensions": ["D1_governing_equations", "D2_constitutive_symmetry", "D5_physical_interpretation"],
        "policy_status": "provisional_heuristic",
        "rubric": {
            "D1": "Strict closure of governing PDEs, potential representations, boundary regularity, and kinematic assumptions.",
            "D2": "Thermodynamic admissibility, strain energy positive-definiteness, and material symmetry justification.",
            "D3": "Clear traction and displacement jump conditions, contact state, and far-field regularity.",
            "D4": "Rigorous convergence checks and comparison with classical analytical benchmarks.",
            "D5": "In-depth physical explanation of mechanics mechanisms (shielding, deflection, amplification) beyond empirical curve fitting.",
        },
    },
    "ijss": {
        "journal_code": "ijss",
        "full_name": "International Journal of Solids and Structures",
        "focus_description": (
            "Solid mechanics, elasticity/plasticity, structural and continuum formulations, "
            "computational mechanics validation, and clear boundary value problems."
        ),
        "priority_dimensions": ["D1_governing_equations", "D3_boundary_interface", "D4_validation_convergence"],
        "policy_status": "provisional_heuristic",
        "rubric": {
            "D1": "Well-posed boundary value problem formulation with complete governing equations and domain definitions.",
            "D2": "Appropriate constitutive laws with verified symmetry and material orientation.",
            "D3": "Exhaustive boundary and interface condition specifications with explicit sign conventions.",
            "D4": "Systematic discretization convergence, mesh sensitivity studies, and error metrics.",
            "D5": "Physical interpretation of structural or material response under prescribed loading.",
        },
    },
    "efm": {
        "journal_code": "efm",
        "full_name": "Engineering Fracture Mechanics",
        "focus_description": (
            "Fracture mechanics, crack propagation, Stress Intensity Factors (SIF), energy release rates, "
            "crack path prediction, fatigue, and experimental/numerical fracture benchmarks."
        ),
        "priority_dimensions": ["D3_boundary_interface", "D4_validation_convergence", "D5_physical_interpretation"],
        "policy_status": "provisional_heuristic",
        "rubric": {
            "D1": "Accurate crack model geometry, coordinate systems, and crack-tip field definitions.",
            "D2": "Fracture criteria, constitutive relations, and crack-tip yield or cohesive zone formulations.",
            "D3": "Traction-free crack surface conditions, crack-face contact, and far-field stresses.",
            "D4": "Benchmark comparison against Tada-Paris-Irwin or Sneddon/Westergaard solutions and mesh refinement near tips.",
            "D5": "Physical mechanisms of fracture resistance, crack shielding/amplification, and failure transitions.",
        },
    },
    "acta_mech_sin": {
        "journal_code": "acta_mech_sin",
        "full_name": "Acta Mechanica Sinica",
        "focus_description": (
            "Broad theoretical, computational, and applied mechanics, emphasizing mathematical clarity, "
            "analytical derivations, and clear physical mechanics contributions."
        ),
        "priority_dimensions": ["D1_governing_equations", "D2_constitutive_symmetry", "D4_validation_convergence"],
        "policy_status": "provisional_heuristic",
        "rubric": {
            "D1": "Complete mathematical formulation with transparent definitions of coordinate frames and balance laws.",
            "D2": "Constitutive validity, symmetry coordinates, and admissible parameter domains.",
            "D3": "Consistent boundary conditions and interface continuity.",
            "D4": "Numerical/analytical verification with independent literature comparison.",
            "D5": "Clear articulation of novelty and mechanics significance.",
        },
    },
    "generic": {
        "journal_code": "generic",
        "full_name": "Generic Mechanics Journal",
        "focus_description": "Standard peer review criteria for solid mechanics, fracture mechanics, and elasticity.",
        "priority_dimensions": [
            "D1_governing_equations",
            "D2_constitutive_symmetry",
            "D3_boundary_interface",
            "D4_validation_convergence",
            "D5_physical_interpretation",
        ],
        "policy_status": "provisional_heuristic",
        "rubric": {
            "D1": "Mathematical formulation completeness and closed boundary value problem.",
            "D2": "Material constitutive admissibility and symmetry.",
            "D3": "Boundary and interface condition clarity.",
            "D4": "Benchmark validation and convergence checks.",
            "D5": "Physical mechanism interpretation and scope bounds.",
        },
    },
}


@dataclass
class ReviewFinding:
    """Represents a specific simulated peer review observation."""
    id: str
    dimension: str  # D1_governing_equations, D2_constitutive_symmetry, etc.
    severity: str   # "major", "minor", "suggestion"
    criterion: str
    manuscript_anchor: str
    observation: str
    reasoning: str
    requested_change: str
    acceptance_check: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "dimension": self.dimension,
            "severity": self.severity,
            "criterion": self.criterion,
            "manuscript_anchor": self.manuscript_anchor,
            "observation": self.observation,
            "reasoning": self.reasoning,
            "requested_change": self.requested_change,
            "acceptance_check": self.acceptance_check,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewFinding":
        return cls(
            id=str(data.get("id", "")),
            dimension=str(data.get("dimension", "")),
            severity=str(data.get("severity", "minor")),
            criterion=str(data.get("criterion", "")),
            manuscript_anchor=str(data.get("manuscript_anchor", "")),
            observation=str(data.get("observation", "")),
            reasoning=str(data.get("reasoning", "")),
            requested_change=str(data.get("requested_change", "")),
            acceptance_check=str(data.get("acceptance_check", "")),
        )


def get_journal_profile(journal: str) -> Dict[str, Any]:
    """Retrieve journal profile heuristics or fallback to generic mechanics."""
    key = journal.lower().replace("-", "_").replace(" ", "_")
    return JOURNAL_PROFILES.get(key, JOURNAL_PROFILES["generic"])


def audit_scientific_soundness(
    manuscript_text: str,
    data_evidence: Optional[List[Dict[str, Any]]] = None,
    journal: str = "jmps",
) -> Dict[str, Any]:
    """
    Perform a 5-dimensional scientific soundness audit of a mechanics manuscript:
    - D1: Governing Equations Completeness
    - D2: Constitutive, Symmetry & Admissibility
    - D3: Boundary & Interface Conditions
    - D4: Validation, Convergence & Reproducibility
    - D5: Physical Interpretation & Mechanism
    """
    profile = get_journal_profile(journal)
    findings: List[ReviewFinding] = []
    dimension_statuses: Dict[str, str] = {}
    finding_counter = 1

    text_lower = manuscript_text.lower()

    # -------------------------------------------------------------------------
    # Dimension 1: Governing Equations Completeness
    # -------------------------------------------------------------------------
    d1_concerns = []
    has_coord = bool(re.search(r"(?:coordinate\s+system|cartesian|polar|cylindrical|\(x,\s*y\)|\(r,\s*\\theta\)|\(x_1,\s*x_2\))", text_lower))
    has_equilibrium = bool(re.search(r"(?:equilibrium|balance\s+of\s+momentum|navier|cauchy|\\sigma_\{?ij,j\}?|\\nabla\s*\\cdot\s*\\sigma)", text_lower))
    has_potentials = bool(re.search(r"(?:potential\s+function|airy|papkovich|stroh|westergaard|kolosov|muskhelishvili)", text_lower))

    if not has_coord:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D1_governing_equations",
            severity="minor",
            criterion="Coordinate Frame Definition",
            manuscript_anchor="Problem Formulation",
            observation="No explicit coordinate system (Cartesian, polar, or material axes) is defined.",
            reasoning="Mechanics boundary value problems require explicit coordinate definitions to prevent tensor component ambiguity.",
            requested_change="Define the global reference frame and orientation (e.g. Cartesian (x, y, z) with x along the crack line).",
            acceptance_check="Check that coordinate axes and orientation are clearly stated in the formulation section.",
        )
        findings.append(f)
        d1_concerns.append(f)
        finding_counter += 1

    if not has_equilibrium and not has_potentials:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D1_governing_equations",
            severity="major",
            criterion="Governing Field Equations",
            manuscript_anchor="Theoretical Formulation",
            observation="Field equilibrium equations or equivalent potential representations are missing or incomplete.",
            reasoning="Continuum mechanics formulations must state balance of linear momentum or governing PDE closure.",
            requested_change="Provide governing differential equations (e.g. Navier-Cauchy equations or biharmonic Airy potential).",
            acceptance_check="Verify field equations are explicitly stated with differential operators defined.",
        )
        findings.append(f)
        d1_concerns.append(f)
        finding_counter += 1

    dimension_statuses["D1_governing_equations"] = "concern" if d1_concerns else "supported"

    # -------------------------------------------------------------------------
    # Dimension 2: Constitutive, Symmetry & Admissibility
    # -------------------------------------------------------------------------
    d2_concerns = []
    has_constitutive = bool(re.search(r"(?:hooke|constitutive|stiffness\s+matrix|elastic\s+modulus|poisson|young's|\be\s*=\s*\d+|\bnu\s*=\s*|c_\{?11\}?|c_\{?ijkl\}?)", text_lower))
    has_symmetry = bool(re.search(r"(?:isotropic|transversely\s+isotropic|orthotropic|anisotropic|material\s+symmetry)", text_lower))

    if not has_constitutive:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D2_constitutive_symmetry",
            severity="major",
            criterion="Constitutive Law Completeness",
            manuscript_anchor="Constitutive Relations",
            observation="No constitutive relation or elastic material tensor is specified.",
            reasoning="Continuum analysis cannot predict stresses or displacements without a defined stress-strain relationship.",
            requested_change="State the constitutive relation (e.g. generalized Hooke's law) with elastic constants.",
            acceptance_check="Verify elastic parameters (E, nu or C_ijkl) and constitutive equations are clearly given.",
        )
        findings.append(f)
        d2_concerns.append(f)
        finding_counter += 1

    if has_constitutive and not has_symmetry:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D2_constitutive_symmetry",
            severity="minor",
            criterion="Material Symmetry Specification",
            manuscript_anchor="Constitutive Relations",
            observation="Constitutive parameters appear without stating the assumed material symmetry class.",
            reasoning="Elastic tensors depend on symmetry (isotropy, transverse isotropy, orthotropy); omitting this introduces ambiguity.",
            requested_change="Explicitly identify the material symmetry class and principal material directions.",
            acceptance_check="Check that material symmetry classification is stated in the constitutive section.",
        )
        findings.append(f)
        d2_concerns.append(f)
        finding_counter += 1

    dimension_statuses["D2_constitutive_symmetry"] = "concern" if d2_concerns else "supported"

    # -------------------------------------------------------------------------
    # Dimension 3: Boundary & Interface Conditions
    # -------------------------------------------------------------------------
    d3_concerns = []
    has_bc = bool(re.search(r"(?:boundary\s+condition|traction[- ]free|clamped|prescribed|far[- ]field|interface\s+condition)", text_lower))
    has_crack_face = bool(re.search(r"(?:crack\s+face|crack\s+surface|traction[- ]free\s+crack|contact|cohesive)", text_lower))
    is_fracture_paper = bool(re.search(r"(?:crack|fracture|sif|stress\s+intensity)", text_lower))

    if not has_bc:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D3_boundary_interface",
            severity="major",
            criterion="Boundary Conditions Completeness",
            manuscript_anchor="Boundary Conditions",
            observation="Boundary conditions on the domain boundaries or at infinity are not specified.",
            reasoning="Elliptic PDEs in linear elasticity have unique solutions only when admissible boundary conditions are fully posed.",
            requested_change="Specify essential (displacement) and natural (traction) boundary conditions across all domain boundaries.",
            acceptance_check="Confirm all outer and inner boundary conditions are mathematically stated.",
        )
        findings.append(f)
        d3_concerns.append(f)
        finding_counter += 1

    if is_fracture_paper and not has_crack_face:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D3_boundary_interface",
            severity="minor",
            criterion="Crack-Face Traction Specification",
            manuscript_anchor="Crack Formulation",
            observation="Crack surfaces are modeled without stating whether crack faces are traction-free, pressurized, or in contact.",
            reasoning="Crack boundary conditions directly determine the singularity order and SIF normalization.",
            requested_change="Explicitly declare crack face boundary conditions (e.g. sigma_yy(x, 0) = 0 for |x| < a).",
            acceptance_check="Verify crack-face traction boundary condition is stated mathematically.",
        )
        findings.append(f)
        d3_concerns.append(f)
        finding_counter += 1

    dimension_statuses["D3_boundary_interface"] = "concern" if d3_concerns else "supported"

    # -------------------------------------------------------------------------
    # Dimension 4: Validation, Convergence & Reproducibility
    # -------------------------------------------------------------------------
    d4_concerns = []
    has_validation = bool(re.search(r"(?:validation|benchmark|comparison|verified|westergaard|tada|sneddon|analytical\s+solution)", text_lower))
    has_convergence = bool(re.search(r"(?:convergence|mesh\s+refinement|quadrature|grid\s+independen|h-refinement|error\s+norm)", text_lower))
    has_numerical = bool(re.search(r"(?:fem|fea|finite\s+element|numerical|boundary\s+element|bifem)", text_lower))

    if not has_validation:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D4_validation_convergence",
            severity="major",
            criterion="Independent Benchmark Validation",
            manuscript_anchor="Numerical Results / Validation",
            observation="Manuscript lacks comparison against established analytical benchmarks or independent solutions.",
            reasoning="Computational mechanics simulations require independent benchmark comparison to establish accuracy.",
            requested_change="Compare proposed results against known closed-form solutions (e.g. Westergaard / Sneddon) in appropriate limiting cases.",
            acceptance_check="Confirm comparison against independent literature benchmark is included with quantitative agreement.",
        )
        findings.append(f)
        d4_concerns.append(f)
        finding_counter += 1

    if has_numerical and not has_convergence:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D4_validation_convergence",
            severity="minor",
            criterion="Discretization Convergence Analysis",
            manuscript_anchor="Numerical Methods",
            observation="Numerical computations are presented without a mesh refinement or numerical convergence study.",
            reasoning="Numerical integrity in fracture mechanics requires demonstrating grid/mesh independence, particularly near stress singularities.",
            requested_change="Provide a convergence curve or table demonstrating mesh independence of key quantities (SIF or energy release rate).",
            acceptance_check="Verify convergence data or error norm vs mesh size is included.",
        )
        findings.append(f)
        d4_concerns.append(f)
        finding_counter += 1

    dimension_statuses["D4_validation_convergence"] = "concern" if d4_concerns else "supported"

    # -------------------------------------------------------------------------
    # Dimension 5: Physical Interpretation & Mechanism
    # -------------------------------------------------------------------------
    d5_concerns = []
    has_mechanism = bool(re.search(r"(?:mechanism|shielding|amplification|deflection|interaction|toughening|energy\s+dissipation|stress\s+redistribution)", text_lower))

    if not has_mechanism:
        f = ReviewFinding(
            id=f"RF_{finding_counter:03d}",
            dimension="D5_physical_interpretation",
            severity="minor",
            criterion="Physical Mechanism Articulation",
            manuscript_anchor="Discussion",
            observation="Results are presented primarily as numerical data without detailing the underlying physical mechanics mechanisms.",
            reasoning="Journal standards (especially JMPS and EFM) require attributing observed trends to governing physical mechanisms.",
            requested_change="Provide physical explanation for the observed behavior (e.g. stress redistribution, elastic mismatch, or shielding mechanisms).",
            acceptance_check="Confirm discussion articulates the underlying physical mechanisms driving the observed phenomena.",
        )
        findings.append(f)
        d5_concerns.append(f)
        finding_counter += 1

    dimension_statuses["D5_physical_interpretation"] = "concern" if d5_concerns else "supported"

    major_count = sum(1 for f in findings if f.severity == "major")
    minor_count = sum(1 for f in findings if f.severity == "minor")

    if major_count == 0 and minor_count == 0:
        overall = "sound"
    elif major_count == 0:
        overall = "minor_concerns"
    elif major_count <= 2:
        overall = "major_concerns"
    else:
        overall = "incomplete"

    recommendations = []
    for f in findings:
        recommendations.append({
            "finding_id": f.id,
            "dimension": f.dimension,
            "priority": "High" if f.severity == "major" else "Medium",
            "action": f.requested_change,
            "verification": f.acceptance_check,
        })

    return {
        "journal": journal,
        "journal_profile": profile,
        "overall_soundness": overall,
        "major_concerns_count": major_count,
        "minor_concerns_count": minor_count,
        "dimensions": {
            dim: {
                "name": _dim_display_name(dim),
                "status": dimension_statuses.get(dim, "not_assessed"),
                "is_priority_for_journal": dim in profile.get("priority_dimensions", []),
                "findings": [f.to_dict() for f in findings if f.dimension == dim],
            }
            for dim in [
                "D1_governing_equations",
                "D2_constitutive_symmetry",
                "D3_boundary_interface",
                "D4_validation_convergence",
                "D5_physical_interpretation",
            ]
        },
        "all_findings": [f.to_dict() for f in findings],
        "actionable_recommendations": recommendations,
    }


def _dim_display_name(dim_key: str) -> str:
    mapping = {
        "D1_governing_equations": "1. Governing Equations Completeness",
        "D2_constitutive_symmetry": "2. Constitutive, Symmetry & Admissibility",
        "D3_boundary_interface": "3. Boundary & Interface Conditions",
        "D4_validation_convergence": "4. Validation, Convergence & Reproducibility",
        "D5_physical_interpretation": "5. Physical Interpretation & Mechanism",
    }
    return mapping.get(dim_key, dim_key)


def generate_review_report_markdown(review_result: Dict[str, Any]) -> str:
    """
    Generate professional, publication-grade simulated peer review report in Markdown.
    """
    profile = review_result.get("journal_profile", {})
    journal_name = profile.get("full_name", review_result.get("journal", "Mechanics Journal"))
    overall = review_result.get("overall_soundness", "evaluated")
    all_findings = review_result.get("all_findings", [])
    dimensions = review_result.get("dimensions", {})
    code_quote = chr(96)

    lines = [
        f"# Simulated Peer Review Report: {journal_name}",
        "",
        "> **Notice**: This simulated peer review report is generated for author revision and manuscript improvement.",
        "> It provides deterministic, evidence-anchored mechanics evaluation and does not represent an official editorial decision.",
        "",
        "## 1. Evaluation Summary",
        f"- **Target Journal**: {journal_name} ({code_quote}{review_result.get('journal', 'generic')}{code_quote})",
        f"- **Overall Scientific Soundness**: {code_quote}{overall.upper()}{code_quote}",
        f"- **Major Concerns**: {review_result.get('major_concerns_count', 0)}",
        f"- **Minor / Formatting Concerns**: {review_result.get('minor_concerns_count', 0)}",
        "",
        "## 2. Five-Dimensional Soundness Matrix",
        "",
        "| Dimension | Evaluation | Priority for Journal | Findings |",
        "|---|---|---|---|",
    ]

    for dim_key, dim_data in dimensions.items():
        if dim_data['status'] == 'supported':
            status_badge = "SUPPORTED"
        elif dim_data['status'] == 'concern':
            status_badge = "CONCERN"
        else:
            status_badge = "NOT ASSESSED"

        priority_marker = "High Priority" if dim_data.get("is_priority_for_journal") else "Standard"
        count = len(dim_data.get("findings", []))
        lines.append(f"| {dim_data['name']} | {status_badge} | {priority_marker} | {count} issue(s) |")

    lines.extend([
        "",
        "## 3. Major Scientific Concerns",
        "",
    ])

    major_findings = [f for f in all_findings if f["severity"] == "major"]
    if not major_findings:
        lines.append("No major theoretical or integrity concerns identified.\n")
    else:
        for f in major_findings:
            lines.extend([
                f"### [{f['id']}] {f['criterion']} ({_dim_display_name(f['dimension'])})",
                f"- **Manuscript Location**: {code_quote}{f['manuscript_anchor']}{code_quote}",
                f"- **Observation**: {f['observation']}",
                f"- **Scientific Reasoning**: {f['reasoning']}",
                f"- **Requested Change**: {f['requested_change']}",
                f"- **Acceptance Check**: {code_quote}{f['acceptance_check']}{code_quote}",
                "",
            ])

    lines.extend([
        "## 4. Minor Revisions & Scientific Clarifications",
        "",
    ])

    minor_findings = [f for f in all_findings if f["severity"] in ("minor", "suggestion")]
    if not minor_findings:
        lines.append("No minor points identified.\n")
    else:
        for f in minor_findings:
            lines.extend([
                f"### [{f['id']}] {f['criterion']}",
                f"- **Location**: {code_quote}{f['manuscript_anchor']}{code_quote}",
                f"- **Observation**: {f['observation']}",
                f"- **Requested Clarification**: {f['requested_change']}",
                "",
            ])

    lines.extend([
        "## 5. Actionable Author Checklist",
        "",
    ])

    recs = review_result.get("actionable_recommendations", [])
    if not recs:
        lines.append("All mechanics soundness criteria currently satisfied.\n")
    else:
        for i, r in enumerate(recs, 1):
            lines.append(f"- [ ] **[{r['priority']}]** ({r['finding_id']}): {r['action']}")

    lines.append("")
    return "\n".join(lines)


def compare_revision(previous_review: Dict[str, Any], revised_text: str) -> Dict[str, Any]:
    """
    Compare revised manuscript text against a previous peer review finding set:
    - Checks whether each previous finding has been resolved, is still persisting, or if new issues emerged.
    - Generates resolution ledger.
    """
    prev_findings = previous_review.get("all_findings", [])
    journal = previous_review.get("journal", "generic")

    current_audit = audit_scientific_soundness(revised_text, journal=journal)
    curr_findings = current_audit.get("all_findings", [])

    resolved: List[Dict[str, Any]] = []
    persisting: List[Dict[str, Any]] = []

    curr_criteria = {f["criterion"]: f for f in curr_findings}

    for pf in prev_findings:
        crit = pf["criterion"]
        if crit not in curr_criteria:
            resolved.append({
                "finding_id": pf["id"],
                "criterion": pf["criterion"],
                "dimension": pf["dimension"],
                "status": "resolved",
                "original_request": pf["requested_change"],
            })
        else:
            persisting.append({
                "finding_id": pf["id"],
                "criterion": pf["criterion"],
                "dimension": pf["dimension"],
                "status": "persisting",
                "remaining_issue": curr_criteria[crit]["observation"],
            })

    prev_criteria = {pf["criterion"] for pf in prev_findings}
    new_findings = [f for f in curr_findings if f["criterion"] not in prev_criteria]

    summary_msg = (
        f"Revision comparison complete: {len(resolved)} finding(s) resolved, "
        f"{len(persisting)} persisting, {len(new_findings)} new issue(s) detected."
    )

    return {
        "status": "resolved" if len(persisting) == 0 and len(resolved) > 0 else ("improved" if len(resolved) > 0 else "unresolved"),
        "summary": summary_msg,
        "resolved_count": len(resolved),
        "persisting_count": len(persisting),
        "new_findings_count": len(new_findings),
        "resolved": resolved,
        "persisting": persisting,
        "new_findings": new_findings,
        "current_overall_soundness": current_audit["overall_soundness"],
    }


def prepare_review_package(
    manuscript_text: str,
    data_evidence: Optional[List[Dict[str, Any]]] = None,
    journal: str = "jmps",
) -> Dict[str, Any]:
    """
    Prepare a comprehensive review task package for external reviewer subagents or host LLM.
    """
    audit_res = audit_scientific_soundness(manuscript_text, data_evidence=data_evidence, journal=journal)
    source_hash = hashlib.sha256(manuscript_text.encode("utf-8")).hexdigest()

    return {
        "status": "review_package_ready",
        "journal": journal,
        "journal_name": audit_res["journal_profile"]["full_name"],
        "source_hash": source_hash,
        "soundness_audit": audit_res,
        "instructions": [
            "Evaluate manuscript based on the 5-dimensional soundness matrix.",
            "Formulate actionable, constructive reviewer feedback without predicting acceptance probability.",
            "Verify that governing equations are closed and boundary conditions are explicitly posed.",
            "Check that benchmark comparisons are independent and not self-referential.",
        ],
        "output_schema_expected": {
            "review_report_markdown": "string",
            "findings": "list",
            "recommendation_summary": "string",
        },
    }
