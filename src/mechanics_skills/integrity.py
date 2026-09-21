import math
import re
"""
Core Integrity Foundation for Mechanics Research and Data Integrity.
Provides Finding dataclass, ConventionRegistry, DataProvenance,
and verification functions for data provenance, constitutive admissibility,
and SIF normalizations.
"""

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


@dataclass
class Finding:
    """
    Standardized integrity and validation finding across G1-G7 categories.
    """
    severity: str  # "critical", "warning", "info"
    category: str  # "G1", "G2", "G3", "G4", "G5", "G6", "G7"
    message: str
    field: str = ""
    context: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "field": self.field,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        return cls(
            severity=str(data.get("severity", "info")),
            category=str(data.get("category", "G1")),
            message=str(data.get("message", "")),
            field=str(data.get("field", "")),
            context=dict(data.get("context", {})),
        )


@dataclass
class ConventionRegistry:
    """
    Holds domain conventions for stress components, sign conventions,
    SIF definitions, COD definitions, and unit scales.
    """
    stress_components: str = "cauchy"
    sign_convention: str = "tension_positive"
    sif_normalization: str = "standard"  # "standard" (K_I = sqrt(pi)*k_I) vs "without_sqrt_pi"
    displacement_definition: str = "single_side_w"  # "single_side_w" vs "total_cod_2w"
    unit_scales: Dict[str, str] = dataclasses.field(default_factory=lambda: {
        "stress": "MPa",
        "length": "mm",
        "sif": "MPa*sqrt(m)",
        "displacement": "mm",
        "energy_release_rate": "J/m^2",
    })
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stress_components": self.stress_components,
            "sign_convention": self.sign_convention,
            "sif_normalization": self.sif_normalization,
            "displacement_definition": self.displacement_definition,
            "unit_scales": self.unit_scales,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConventionRegistry":
        return cls(
            stress_components=str(data.get("stress_components", "cauchy")),
            sign_convention=str(data.get("sign_convention", "tension_positive")),
            sif_normalization=str(data.get("sif_normalization", "standard")),
            displacement_definition=str(data.get("displacement_definition", "single_side_w")),
            unit_scales=dict(data.get("unit_scales", {
                "stress": "MPa",
                "length": "mm",
                "sif": "MPa*sqrt(m)",
                "displacement": "mm",
                "energy_release_rate": "J/m^2",
            })),
            extra=dict(data.get("extra", {})),
        )


@dataclass
class DataProvenance:
    """
    Holds cryptographic audit hash (SHA-256) and source metadata for raw datasets.
    """
    sha256: str
    source_path: Optional[str] = None
    generation_timestamp: Optional[str] = None
    record_count: Optional[int] = None
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sha256": self.sha256,
            "source_path": self.source_path,
            "generation_timestamp": self.generation_timestamp,
            "record_count": self.record_count,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataProvenance":
        return cls(
            sha256=str(data.get("sha256", "")),
            source_path=data.get("source_path"),
            generation_timestamp=data.get("generation_timestamp"),
            record_count=data.get("record_count"),
            extra=dict(data.get("extra", {})),
        )


def audit_data_provenance(data: Any, source_path: Optional[str] = None) -> str:
    """
    Compute deterministic SHA-256 hash string for raw numerical datasets,
    numpy arrays, dictionaries, or files on disk.
    """
    if isinstance(data, bytes):
        raw_bytes = data
    elif isinstance(data, (str, Path)) and Path(str(data)).is_file():
        raw_bytes = Path(str(data)).read_bytes()
    elif np is not None and isinstance(data, np.ndarray):
        raw_bytes = np.ascontiguousarray(data).tobytes()
    elif isinstance(data, (dict, list)):
        raw_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    elif isinstance(data, str):
        raw_bytes = data.encode("utf-8")
    else:
        raw_bytes = str(data).encode("utf-8")

    return hashlib.sha256(raw_bytes).hexdigest()


def create_data_provenance(data: Any, source_path: Optional[str] = None) -> DataProvenance:
    """
    Create a DataProvenance record with SHA-256 hash and UTC timestamp.
    """
    h = audit_data_provenance(data, source_path=source_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    count = None
    if isinstance(data, (list, tuple)):
        count = len(data)
    elif np is not None and isinstance(data, np.ndarray):
        count = int(data.size)
    return DataProvenance(
        sha256=h,
        source_path=str(source_path) if source_path else None,
        generation_timestamp=now_iso,
        record_count=count,
    )


def check_constitutive_admissibility(
    stiffness_matrix: Union[List[List[float]], np.ndarray],
    symmetry: str = "isotropic",
    tol: float = 1e-6,
) -> List[Finding]:
    """
    Verify major symmetry, positive definiteness (thermodynamic stability),
    and material symmetry admissibility of a stiffness matrix.
    """
    findings: List[Finding] = []
    if not HAS_NUMPY or np is None:
        findings.append(
            Finding(
                severity="warning",
                category="G1",
                message="NumPy is not installed; skipping eigenvalue positive-definiteness calculation.",
                field="stiffness_matrix",
            )
        )
        return findings
    C = np.array(stiffness_matrix, dtype=float)

    if C.ndim != 2 or C.shape[0] != C.shape[1]:
        findings.append(
            Finding(
                severity="critical",
                category="G1",
                message=f"Stiffness matrix must be 2D square matrix, got shape {C.shape}",
                field="stiffness_matrix",
                context={"shape": list(C.shape)},
            )
        )
        return findings

    # 1. Major symmetry C_ij == C_ji
    asymmetry = float(np.max(np.abs(C - C.T)))
    if asymmetry > tol:
        findings.append(
            Finding(
                severity="critical",
                category="G1",
                message=f"Stiffness matrix violates major symmetry (max |C_ij - C_ji| = {asymmetry:.3e} > {tol})",
                field="stiffness_matrix",
                context={"max_asymmetry": asymmetry, "tol": tol},
            )
        )

    # 2. Positive definiteness (strain energy positivity / thermodynamic stability)
    sym_C = (C + C.T) / 2.0
    eigvals = np.linalg.eigvalsh(sym_C)
    min_eig = float(np.min(eigvals))

    if min_eig <= 0:
        findings.append(
            Finding(
                severity="critical",
                category="G1",
                message=f"Stiffness matrix is not positive definite (min eigenvalue = {min_eig:.3e} <= 0); violates thermodynamic admissibility",
                field="stiffness_matrix",
                context={"min_eigenvalue": min_eig, "eigenvalues": [float(e) for e in eigvals]},
            )
        )
    elif min_eig < 1e-5:
        findings.append(
            Finding(
                severity="warning",
                category="G1",
                message=f"Stiffness matrix is ill-conditioned or near-singular (min eigenvalue = {min_eig:.3e})",
                field="stiffness_matrix",
                context={"min_eigenvalue": min_eig},
            )
        )

    # 3. Symmetry constraints
    sym_clean = symmetry.lower().replace("-", "_").replace(" ", "_")
    if sym_clean in ("isotropic", "iso") and C.shape == (6, 6):
        # Diagonal isotropic constraints: C11 == C22 == C33
        diag_diff = max(abs(C[0, 0] - C[1, 1]), abs(C[1, 1] - C[2, 2]))
        # Off-diagonal: C12 == C13 == C23
        off_diff = max(abs(C[0, 1] - C[0, 2]), abs(C[0, 2] - C[1, 2]))
        # Shear: C44 == C55 == C66
        shear_diff = max(abs(C[3, 3] - C[4, 4]), abs(C[4, 4] - C[5, 5]))
        # Isotropic relation: C44 == (C11 - C12) / 2
        iso_rel = abs(C[3, 3] - (C[0, 0] - C[0, 1]) / 2.0)

        if max(diag_diff, off_diff, shear_diff, iso_rel) > tol * 10:
            findings.append(
                Finding(
                    severity="warning",
                    category="G7",
                    message="Stiffness matrix violates isotropic symmetry constraints (C11=C22=C33, C44=(C11-C12)/2)",
                    field="symmetry",
                    context={
                        "diag_diff": float(diag_diff),
                        "shear_diff": float(shear_diff),
                        "iso_relation_diff": float(iso_rel),
                    },
                )
            )

    elif sym_clean in ("transversely_isotropic", "ti", "transverse_isotropy") and C.shape == (6, 6):
        # In-plane isotropy: C11 == C22, C13 == C23, C44 == C55, C66 == (C11 - C12) / 2
        ti_diag = abs(C[0, 0] - C[1, 1])
        ti_off = abs(C[0, 2] - C[1, 2])
        ti_shear = abs(C[3, 3] - C[4, 4])
        ti_inplane_shear = abs(C[5, 5] - (C[0, 0] - C[0, 1]) / 2.0)

        if max(ti_diag, ti_off, ti_shear, ti_inplane_shear) > tol * 10:
            findings.append(
                Finding(
                    severity="warning",
                    category="G7",
                    message="Stiffness matrix violates transverse isotropy constraints (C11=C22, C13=C23, C66=(C11-C12)/2)",
                    field="symmetry",
                    context={
                        "inplane_diag_diff": float(ti_diag),
                        "inplane_shear_diff": float(ti_inplane_shear),
                    },
                )
            )

    return findings


def check_sif_normalization(
    sif_val: float,
    baseline_val: float,
    definition: str = "standard",
) -> List[Finding]:
    """
    Verify SIF normalization ratio, detect division by zero, negative Mode I values,
    or potential sqrt(pi) factor mismatches between Irwin (K_I = sigma*sqrt(pi*a))
    and Sneddon/Barenblatt (k_I = sigma*sqrt(a)) definitions.
    """
    findings: List[Finding] = []

    if abs(baseline_val) < 1e-12:
        findings.append(
            Finding(
                severity="critical",
                category="G1",
                message="Baseline SIF value K_0 is zero or near-zero; normalization undefined",
                field="baseline_val",
                context={"baseline_val": baseline_val},
            )
        )
        return findings

    ratio = sif_val / baseline_val

    # Check for negative Mode I SIF under tensile baseline
    if baseline_val > 0 and sif_val < 0:
        findings.append(
            Finding(
                severity="warning",
                category="G1",
                message=f"Mode I SIF is negative ({sif_val:.4f}) under positive tensile baseline ({baseline_val:.4f})",
                field="sif_val",
                context={"sif_val": sif_val, "baseline_val": baseline_val, "ratio": ratio},
            )
        )

    # Detect sqrt(pi) mismatch
    sqrt_pi = float(math.sqrt(math.pi))  # ~ 1.77245
    inv_sqrt_pi = 1.0 / sqrt_pi      # ~ 0.56419

    if abs(ratio - sqrt_pi) < 0.08:
        findings.append(
            Finding(
                severity="warning",
                category="G1",
                message=f"SIF ratio {ratio:.4f} is close to sqrt(pi) ({sqrt_pi:.4f}); potential mismatch between K_I = sigma*sqrt(pi*a) and k_I = sigma*sqrt(a)",
                field="sif_val",
                context={"ratio": ratio, "suspected_factor": "sqrt(pi)"},
            )
        )
    elif abs(ratio - inv_sqrt_pi) < 0.05:
        findings.append(
            Finding(
                severity="warning",
                category="G1",
                message=f"SIF ratio {ratio:.4f} is close to 1/sqrt(pi) ({inv_sqrt_pi:.4f}); potential mismatch between K_I = sigma*sqrt(pi*a) and k_I = sigma*sqrt(a)",
                field="sif_val",
                context={"ratio": ratio, "suspected_factor": "1/sqrt(pi)"},
            )
        )

    return findings


# -------------------------------------------------------------------------
# Complete Scientific Integrity Pipeline (G1~G7 Gates)
# -------------------------------------------------------------------------

def run_integrity_pipeline(
    manuscript_text: str,
    data_refs: Optional[List[Any]] = None,
    conventions: Optional[Union[Dict[str, Any], ConventionRegistry]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute complete 7-Gate Scientific Integrity Pipeline across mechanics research:
    - G1: Numerical & Units Consistency
    - G2: Citation & Claims Faithfulness
    - G3: Data Provenance & Result Genuineness
    - G4: Benchmark Independence
    - G5: Bug-as-Discovery Check
    - G6: Method Consistency
    - G7: Scope & Assumption Lock
    """
    if conventions is None:
        conv_reg = ConventionRegistry()
    elif isinstance(conventions, dict):
        conv_reg = ConventionRegistry.from_dict(conventions)
    else:
        conv_reg = conventions

    opts = options or {}
    text_lower = manuscript_text.lower()
    all_findings: List[Finding] = []

    # ---------------------------------------------------------------------
    # Gate G1: Implementation & Numerical Consistency
    # ---------------------------------------------------------------------
    g1_findings: List[Finding] = []
    
    # Check stiffness matrix if provided in data_refs or options
    stiffness = opts.get("stiffness_matrix")
    if stiffness is not None:
        sym = opts.get("material_symmetry", "isotropic")
        g1_findings.extend(check_constitutive_admissibility(stiffness, symmetry=sym))

    # Check SIF normalization if values provided in options
    if "sif_val" in opts and "baseline_val" in opts:
        g1_findings.extend(check_sif_normalization(opts["sif_val"], opts["baseline_val"]))

    # Check unit consistency in text
    if re.search(r"\bMPa\b", manuscript_text) and re.search(r"\bGPa\b", manuscript_text):
        g1_findings.append(
            Finding(
                severity="info",
                category="G1",
                message="Text contains both MPa and GPa unit prefixes; ensure consistent unit scaling across formulas.",
                field="unit_scales",
                context={"scales": ["MPa", "GPa"]},
            )
        )

    # ---------------------------------------------------------------------
    # Gate G2: Citation & Claims Faithfulness
    # ---------------------------------------------------------------------
    g2_findings: List[Finding] = []
    
    # Check if abstract is used as full-text source
    if opts.get("source_is_abstract", False):
        g2_findings.append(
            Finding(
                severity="critical",
                category="G2",
                message="Source document is an abstract, not a full-text manuscript. Deep formula and evidence verification cannot be completed.",
                field="source_type",
                context={"source_type": "abstract"},
            )
        )

    # Check for literature references without citation
    uncited_matches = list(re.finditer(r"(?:previous\s+studies|earlier\s+experiments|literature\s+reports|widely\s+reported)\s+(?:show|indicate|prove)", text_lower))
    has_citations = bool(re.search(r"\\cite|\[@[a-zA-Z0-9]", manuscript_text))
    if uncited_matches and not has_citations:
        g2_findings.append(
            Finding(
                severity="warning",
                category="G2",
                message="Manuscript refers to previous studies or literature without providing formal citations (\\cite or [@bibkey]).",
                field="citations",
                context={"match": uncited_matches[0].group(0)},
            )
        )

    # ---------------------------------------------------------------------
    # Gate G3: Data Provenance & Result Genuineness
    # ---------------------------------------------------------------------
    g3_findings: List[Finding] = []
    provenance_records: List[DataProvenance] = []

    if data_refs:
        for i, ref in enumerate(data_refs, 1):
            if isinstance(ref, (str, Path)) and Path(str(ref)).is_file():
                prov = create_data_provenance(Path(str(ref)), source_path=str(ref))
                provenance_records.append(prov)
            elif isinstance(ref, (dict, list)) or (np is not None and isinstance(ref, np.ndarray)):
                prov = create_data_provenance(ref, source_path=f"memory_ref_{i}")
                provenance_records.append(prov)
            elif isinstance(ref, DataProvenance):
                provenance_records.append(ref)
            else:
                prov = create_data_provenance(str(ref), source_path=f"data_ref_{i}")
                provenance_records.append(prov)
    else:
        # If manuscript presents numerical results/curves but provides no data_refs
        has_results = bool(re.search(r"(?:fig(?:ure)?\.?\s*\d+|table\s*\d+|numerical\s+results)", text_lower))
        if has_results:
            g3_findings.append(
                Finding(
                    severity="warning",
                    category="G3",
                    message="Numerical results or figures are presented without accompanying raw data provenance or cryptographic hash audit.",
                    field="data_provenance",
                    context={"recommendation": "Attach data_refs with raw dataset SHA-256 hashes for cryptographic provenance audit."},
                )
            )

    # ---------------------------------------------------------------------
    # Gate G4: Benchmark Independence
    # ---------------------------------------------------------------------
    g4_findings: List[Finding] = []
    
    # Detect self-referential benchmarks (e.g. "verified against our own earlier simulation")
    self_ref_match = re.search(r"(?:verified\s+against\s+(?:our\s+)?(?:own\s+)?(?:in-house\s+|earlier\s+|previous\s+)*(?:own\s+)*(?:code|simulation|model)|validated\s+with\s+the\s+same\s+finite\s+element\s+code)", text_lower)
    if self_ref_match:
        g4_findings.append(
            Finding(
                severity="critical",
                category="G4",
                message=f"Self-referential validation detected: '{self_ref_match.group(0)}'. Independent external benchmarks (analytical solutions or third-party datasets) are mandatory.",
                field="benchmark_independence",
                context={"match": self_ref_match.group(0)},
            )
        )
    elif not re.search(r"(?:westergaard|sneddon|tada|muskhelishvili|analytical\s+benchmark|closed[- ]form|independent\s+experimental)", text_lower):
        if re.search(r"(?:validation|benchmark|verified)", text_lower):
            g4_findings.append(
                Finding(
                    severity="warning",
                    category="G4",
                    message="Validation section does not clearly cite an established independent canonical benchmark (e.g. Westergaard, Sneddon, Tada, or Muskhelishvili).",
                    field="benchmark_independence",
                )
            )

    # ---------------------------------------------------------------------
    # Gate G5: Bug-as-Discovery Check
    # ---------------------------------------------------------------------
    g5_findings: List[Finding] = []
    
    # Detect numerical mesh artifacts described as new discoveries
    bug_matches = list(re.finditer(r"(?:mesh|singularity|boundary\s+layer|numerical\s+spike)\s+(?:reveals?|demonstrates?|discovers?|unveils?)\s+(?:a\s+new|novel|unprecedented|mysterious)\s+(?:physics|mechanism|phenomenon)", text_lower))
    if bug_matches:
        g5_findings.append(
            Finding(
                severity="critical",
                category="G5",
                message=f"Potential numerical bug/singularity mischaracterized as discovery: '{bug_matches[0].group(0)}'. Ensure mesh convergence and boundary residuals are rigorously ruled out.",
                field="bug_as_discovery",
                context={"match": bug_matches[0].group(0)},
            )
        )

    # ---------------------------------------------------------------------
    # Gate G6: Method Consistency
    # ---------------------------------------------------------------------
    g6_findings: List[Finding] = []
    
    # Contradiction: Plane strain claimed with plane stress modulus E, or vice versa
    if "plane strain" in text_lower and re.search(r"effective\s+modulus\s+E'\s*=\s*E\b", manuscript_text):
        g6_findings.append(
            Finding(
                severity="critical",
                category="G6",
                message="Method contradiction: Manuscript specifies plane strain condition but sets effective Young's modulus E' = E instead of E/(1 - nu^2).",
                field="plane_assumption",
                context={"assumption": "plane strain", "effective_modulus": "E"},
            )
        )
    elif "plane stress" in text_lower and re.search(r"effective\s+modulus\s+E'\s*=\s*E\s*/\s*\(?\s*1\s*-\s*\\?(?:nu|\bnu\b)", manuscript_text):
        g6_findings.append(
            Finding(
                severity="critical",
                category="G6",
                message="Method contradiction: Manuscript specifies plane stress condition but sets effective Young's modulus E' = E/(1 - nu^2) instead of E.",
                field="plane_assumption",
                context={"assumption": "plane stress", "effective_modulus": "E/(1-nu^2)"},
            )
        )

    # ---------------------------------------------------------------------
    # Gate G7: Scope & Assumption Lock
    # ---------------------------------------------------------------------
    g7_findings: List[Finding] = []
    
    # Contradiction: Isotropic Hooke's law formulas applied to transversely isotropic solid
    if re.search(r"(?:transversely\s+isotropic|orthotropic|anisotropic)", text_lower):
        if re.search(r"G\s*=\s*E\s*/\s*\(\s*2\s*(?:\*|\s*)?\(\s*1\s*\+\s*\\?(?:nu|\bnu\b)\s*\)\s*\)", manuscript_text):
            g7_findings.append(
                Finding(
                    severity="critical",
                    category="G7",
                    message="Scope violation: Isotropic relation G = E/(2(1+nu)) is applied to anisotropic/transversely isotropic material.",
                    field="material_assumptions",
                    context={"violation": "isotropic shear modulus on anisotropic material"},
                )
            )

    # Aggregate all findings
    all_findings.extend(g1_findings)
    all_findings.extend(g2_findings)
    all_findings.extend(g3_findings)
    all_findings.extend(g4_findings)
    all_findings.extend(g5_findings)
    all_findings.extend(g6_findings)
    all_findings.extend(g7_findings)

    def _eval_status(findings_list: List[Finding]) -> str:
        if any(f.severity == "critical" for f in findings_list):
            return "fail"
        elif any(f.severity == "warning" for f in findings_list):
            return "unknown"
        return "pass"

    gates_summary = {
        "G1": {
            "name": "Implementation & Numerical Consistency",
            "status": _eval_status(g1_findings),
            "findings": [f.to_dict() for f in g1_findings],
            "description": "Dimensional consistency, positive definiteness, and SIF normalizations.",
        },
        "G2": {
            "name": "Citation & Claims Faithfulness",
            "status": _eval_status(g2_findings),
            "findings": [f.to_dict() for f in g2_findings],
            "description": "Citation support for claims and absence of unsupported certainty assertions.",
        },
        "G3": {
            "name": "Data Provenance & Result Genuineness",
            "status": _eval_status(g3_findings),
            "findings": [f.to_dict() for f in g3_findings],
            "provenance_count": len(provenance_records),
            "description": "Cryptographic SHA-256 data hashing and raw evidence tracing.",
        },
        "G4": {
            "name": "Benchmark Independence",
            "status": _eval_status(g4_findings),
            "findings": [f.to_dict() for f in g4_findings],
            "description": "Verification against independent canonical analytical/experimental benchmarks.",
        },
        "G5": {
            "name": "Bug-as-Discovery Check",
            "status": _eval_status(g5_findings),
            "findings": [f.to_dict() for f in g5_findings],
            "description": "Ensuring numerical mesh artifacts or unphysical spikes are not framed as novel physics.",
        },
        "G6": {
            "name": "Method Consistency",
            "status": _eval_status(g6_findings),
            "findings": [f.to_dict() for f in g6_findings],
            "description": "Internal consistency across 2D plane strain/stress assumptions and formulation.",
        },
        "G7": {
            "name": "Scope & Assumption Lock",
            "status": _eval_status(g7_findings),
            "findings": [f.to_dict() for f in g7_findings],
            "description": "Preventing assumption leakage (e.g. isotropic formulas applied to anisotropic solids).",
        },
    }

    # Pipeline readiness
    has_critical = any(f.severity == "critical" for f in all_findings)
    has_warnings = any(f.severity == "warning" for f in all_findings)

    if has_critical:
        readiness = "blocked"
        overall_status = "fail"
    elif has_warnings:
        readiness = "needs_evidence"
        overall_status = "needs_evidence"
    else:
        readiness = "ready_for_author_review"
        overall_status = "pass"

    summary_text = (
        f"Scientific Integrity Pipeline completed with readiness='{readiness}'. "
        f"Total findings: {len(all_findings)} (Critical: {sum(1 for f in all_findings if f.severity == 'critical')}, "
        f"Warning: {sum(1 for f in all_findings if f.severity == 'warning')}, "
        f"Info: {sum(1 for f in all_findings if f.severity == 'info')})."
    )

    return {
        "status": overall_status,
        "readiness": readiness,
        "gates": gates_summary,
        "all_findings": [f.to_dict() for f in all_findings],
        "data_provenances": [p.to_dict() for p in provenance_records],
        "summary": summary_text,
    }
