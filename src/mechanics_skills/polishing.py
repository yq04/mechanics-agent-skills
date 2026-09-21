"""
Mechanics Paper Polishing & Notation Guard.
Phase 7 implementation for mechanics-agent-skills:
- Protection zone tokenizer (display math, inline math, citations, cross-refs, code, units, URLs)
- Cryptographic SHA-256 integrity preservation for mathematical formulas
- Notation and terminology guard for mechanics ambiguities (COD vs w, k_I vs K_I, shear strain, etc.)
- AI cliché & fluff stripper with context-aware replacement recommendations
- Edit proposal validation and deterministic safe application
"""

import dataclasses
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from mechanics_skills.integrity import Finding, ConventionRegistry


@dataclass
class ProtectedZone:
    """Represents a strictly protected region in manuscript text."""
    id: str
    zone_type: str  # "math_display", "math_inline", "citation", "cross_ref", "code", "unit_quantity", "url"
    start: int
    end: int
    content: str
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "zone_type": self.zone_type,
            "start": self.start,
            "end": self.end,
            "content": self.content,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtectedZone":
        return cls(
            id=str(data.get("id", "")),
            zone_type=str(data.get("zone_type", "unknown")),
            start=int(data.get("start", 0)),
            end=int(data.get("end", 0)),
            content=str(data.get("content", "")),
            sha256=str(data.get("sha256", "")),
        )


PROTECTED_PATTERNS = [
    # 1. Display Math Environments
    (
        "math_display",
        re.compile(
            r"\\begin\{(?:equation|align|gather|multline|flalign|alignat)\*?\}[\s\S]*?\\end\{(?:equation|align|gather|multline|flalign|alignat)\*?\}",
            re.MULTILINE,
        ),
    ),
    ("math_display", re.compile(r"\$\$[\s\S]*?\$\$", re.MULTILINE)),
    ("math_display", re.compile(r"\\\[[\s\S]*?\\\]", re.MULTILINE)),
    # 2. Inline Math
    ("math_inline", re.compile(r"\\\([\s\S]*?\\\)")),
    ("math_inline", re.compile(r"(?<!\\)\$(?!\$)(?:\\\$|[^\$\n])+?\$")),
    # 3. Code blocks & inline code (using \x60 for backticks)
    ("code", re.compile(r"\x60{3}[\s\S]*?\x60{3}")),
    ("code", re.compile(r"\x60[^\x60\n]+\x60")),
    # 4. LaTeX Citations & Markdown citations
    (
        "citation",
        re.compile(
            r"\\(?:cite|citep|citet|citeauthor|citeyear|citealt|citealp)\*?(?:\[.*?\])?\{[^}]+\}"
        ),
    ),
    ("citation", re.compile(r"\[@[a-zA-Z0-9_\-:]+(?:\s*;\s*@[a-zA-Z0-9_\-:]+)*\]")),
    # 5. Cross-references & Labels
    ("cross_ref", re.compile(r"\\(?:ref|eqref|label|autoref|pageref)\{[^}]+\}")),
    # 6. Physical quantities with units
    (
        "unit_quantity",
        re.compile(
            r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*(?:GPa|MPa|kPa|Pa|N/m\^2|N/mm\^2|kN|N|mm|cm|m|μm|um|nm|rad|deg|°|J/m\^2|kJ/m\^2|MPa\\sqrt\{m\}|MPa\*m\^0\.5|MPa\s*m\^(?:1/2|0\.5))\b"
        ),
    ),
    # 7. URLs
    ("url", re.compile(r"https?://[^\s)\]>]+")),
]


AI_CLICHE_RULES = [
    {
        "pattern": re.compile(r"\bdelve(?:s|d|ing)?\s+into\b", re.IGNORECASE),
        "word": "delve into",
        "replacement": "investigate, examine, or analyze",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bdelve(?:s|d|ing)?\b", re.IGNORECASE),
        "word": "delve",
        "replacement": "explore, study, or evaluate",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bserves?\s+as\s+a\s+testament\s+to\b", re.IGNORECASE),
        "word": "serves as a testament to",
        "replacement": "demonstrates, validates, or confirms",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\btestament\b", re.IGNORECASE),
        "word": "testament",
        "replacement": "evidence, proof, or demonstration",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bpivotal\b", re.IGNORECASE),
        "word": "pivotal",
        "replacement": "critical, key, or primary",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bfoster(?:s|ed|ing)?\b", re.IGNORECASE),
        "word": "foster",
        "replacement": "promote, induce, or facilitate",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\b(?:rich\s+)?tapestry\b", re.IGNORECASE),
        "word": "tapestry",
        "replacement": "structure, network, or combination",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bunderscore(?:s|d|ing)?\b", re.IGNORECASE),
        "word": "underscores",
        "replacement": "indicates, emphasizes, or highlights",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bcrucial\b", re.IGNORECASE),
        "word": "crucial",
        "replacement": "necessary, essential, or governing",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bparamount\b", re.IGNORECASE),
        "word": "paramount",
        "replacement": "governing, principal, or essential",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bremarkable\b", re.IGNORECASE),
        "word": "remarkable",
        "replacement": "substantial, pronounced, or omit fluff",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\binterplay\b", re.IGNORECASE),
        "word": "interplay",
        "replacement": "coupling, interaction, or mutual effect",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bbeacon\b", re.IGNORECASE),
        "word": "beacon",
        "replacement": "benchmark, reference, or guide",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bmoreover\b", re.IGNORECASE),
        "word": "moreover",
        "replacement": "additionally, furthermore, or rewrite sentence",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bgroundbreaking\b", re.IGNORECASE),
        "word": "groundbreaking",
        "replacement": "novel, new, or omit hype",
        "category": "ai_cliche",
    },
    {
        "pattern": re.compile(r"\bgame-?changing\b", re.IGNORECASE),
        "word": "game-changing",
        "replacement": "transformative, effective, or omit hype",
        "category": "ai_cliche",
    },
]


def extract_protected_zones(text: str) -> List[ProtectedZone]:
    """
    Extract non-overlapping protected zones (math formulas, citations, code,
    cross-references, unit quantities, URLs) with exact byte spans and SHA-256 hashes.
    """
    raw_spans: List[Tuple[int, int, str, str]] = []

    for zone_type, pattern in PROTECTED_PATTERNS:
        for match in pattern.finditer(text):
            raw_spans.append((match.start(), match.end(), zone_type, match.group(0)))

    # Sort primarily by start asc, secondarily by length desc
    raw_spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))

    # Merge / eliminate overlapping spans
    filtered_spans: List[Tuple[int, int, str, str]] = []
    current_end = -1

    for start, end, zone_type, content in raw_spans:
        if start >= current_end:
            filtered_spans.append((start, end, zone_type, content))
            current_end = end

    zones: List[ProtectedZone] = []
    for i, (start, end, ztype, content) in enumerate(filtered_spans, 1):
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        zones.append(
            ProtectedZone(
                id=f"zone_{i:04d}",
                zone_type=ztype,
                start=start,
                end=end,
                content=content,
                sha256=sha,
            )
        )
    return zones


def is_inside_spans(pos: int, spans: List[Tuple[int, int]]) -> bool:
    """Check if character index is within any given spans."""
    for s, e in spans:
        if s <= pos < e:
            return True
    return False


def detect_cliches(text: str, protected_zones: List[ProtectedZone]) -> List[Dict[str, Any]]:
    """
    Detect AI clichés and fluff outside protected zones and quotes.
    """
    protected_spans = [(z.start, z.end) for z in protected_zones]

    quote_spans: List[Tuple[int, int]] = []
    for m in re.finditer(r'["“][^"”\n]+["”]', text):
        quote_spans.append((m.start(), m.end()))
    all_ignored = protected_spans + quote_spans

    cliches_found: List[Dict[str, Any]] = []
    for rule in AI_CLICHE_RULES:
        for match in rule["pattern"].finditer(text):
            start, end = match.start(), match.end()
            if not is_inside_spans(start, all_ignored):
                cliches_found.append({
                    "word": rule["word"],
                    "matched_text": match.group(0),
                    "start": start,
                    "end": end,
                    "replacement_suggestion": rule["replacement"],
                    "rule": rule["category"],
                })

    cliches_found.sort(key=lambda c: c["start"])
    return cliches_found


def detect_notation_warnings(text: str, conventions: Optional[ConventionRegistry] = None) -> List[Finding]:
    """
    Check for high-risk mechanics notation ambiguities and terminological pitfalls.
    """
    warnings: List[Finding] = []

    # 1. COD vs single-side displacement w
    if re.search(r"\bCOD\b", text, re.IGNORECASE) and re.search(r"\bw\b", text):
        has_cod_relation = bool(
            re.search(r"COD\s*=\s*2\s*w", text, re.IGNORECASE)
            or re.search(r"w\s*=\s*(?:COD/2|0\.5\s*COD)", text, re.IGNORECASE)
            or re.search(r"\[u\]", text)
            or re.search(r"displacement\s+jump", text, re.IGNORECASE)
        )
        if not has_cod_relation:
            warnings.append(
                Finding(
                    severity="warning",
                    category="G1",
                    message="Both COD and displacement w are referenced without specifying relationship (COD = 2w for symmetric Mode I, or displacement jump [u]·n).",
                    field="displacement_definition",
                    context={"recommendation": "Clarify whether w denotes single-side displacement (COD = 2w) or total crack opening."},
                )
            )

    # 2. k_I vs K_I normalization (Irwin vs Sneddon/Barenblatt)
    has_big_K = bool(re.search(r"\bK_\{?I\}?\b", text) or re.search(r"K_I\b", text))
    has_small_k = bool(re.search(r"\bk_\{?I\}?\b", text) or re.search(r"\bk_I\b", text))
    if has_big_K and has_small_k:
        has_sif_relation = bool(
            re.search(r"K_\{?I\}?\s*=\s*(?:\\sqrt\{\\pi\}|sqrt\(pi\))\s*\*?\s*k_\{?I\}?", text)
            or re.search(r"k_\{?I\}?\s*=\s*K_\{?I\}?\s*/\s*(?:\\sqrt\{\\pi\}|sqrt\(pi\))", text)
        )
        if not has_sif_relation:
            warnings.append(
                Finding(
                    severity="warning",
                    category="G1",
                    message="Both Irwin K_I and Sneddon/Barenblatt k_I notation appear without explicit normalization formula (K_I = sqrt(pi)*k_I).",
                    field="sif_normalization",
                    context={"recommendation": "State the SIF normalization explicitly to avoid a factor of sqrt(pi) (~1.772) ambiguity."},
                )
            )

    # 3. Engineering shear vs tensorial shear
    has_gamma = bool(re.search(r"\\gamma_\{?x?y\}?", text) or re.search(r"\bgamma_\{?xy\}?", text))
    has_eps_xy = bool(re.search(r"\\varepsilon_\{?xy\}?", text) or re.search(r"\bepsilon_\{?xy\}?", text))
    if has_gamma and has_eps_xy:
        has_shear_relation = bool(
            re.search(r"\\gamma_\{?xy\}?\s*=\s*2\s*\\varepsilon_\{?xy\}?", text)
            or re.search(r"engineering\s+shear", text, re.IGNORECASE)
        )
        if not has_shear_relation:
            warnings.append(
                Finding(
                    severity="warning",
                    category="G1",
                    message="Both engineering shear gamma_xy and tensorial shear epsilon_xy appear without clarifying gamma_xy = 2*epsilon_xy.",
                    field="shear_strain_convention",
                    context={"recommendation": "Explicitly distinguish engineering shear strain from tensorial components in constitutive equations."},
                )
            )

    # 4. Plane stress vs plane strain assumptions
    if re.search(r"plane\s+stress", text, re.IGNORECASE) and re.search(r"plane\s+strain", text, re.IGNORECASE):
        warnings.append(
            Finding(
                severity="info",
                category="G6",
                message="Text mentions both 'plane stress' and 'plane strain'. Ensure effective modulus E' (E vs E/(1-nu^2)) is explicitly distinguished for each section.",
                field="plane_assumption",
                context={"recommendation": "Verify consistent definition of effective elastic modulus E' across 2D formulations."},
            )
        )

    # 5. Overstated scientific claims / exactness tone
    exact_numerical_matches = list(re.finditer(r"(?:FEA|FEM|finite element|numerical)\s+(?:exact|analytical|closed-form)\s+solution", text, re.IGNORECASE))
    if exact_numerical_matches:
        warnings.append(
            Finding(
                severity="warning",
                category="G5",
                message="Text describes numerical/FEA simulation as 'exact solution'. Numerical approximations should be termed converged or high-precision approximations, not closed-form exact solutions.",
                field="exactness_claim",
                context={"match": exact_numerical_matches[0].group(0)},
            )
        )

    # 6. Unqualified universal claims (all/always/unprecedented)
    unqualified_matches = list(re.finditer(r"\b(?:always\s+valid|unprecedented|proved\s+universally|for\s+all\s+materials)\b", text, re.IGNORECASE))
    if unqualified_matches:
        warnings.append(
            Finding(
                severity="warning",
                category="G7",
                message=f"Potentially over-generalized claim detected: '{unqualified_matches[0].group(0)}'. State specific validity bounds (material class, small-strain, linear elasticity).",
                field="claim_scope",
                context={"match": unqualified_matches[0].group(0)},
            )
        )

    # 7. Preferred terminology suggestions
    term_replacements = [
        (re.compile(r"\btransverse\s+isotropic\b", re.IGNORECASE), "transversely isotropic"),
        (re.compile(r"\bcross\s+isotropic\b", re.IGNORECASE), "transversely isotropic"),
        (re.compile(r"\bstress\s+concentration\s+factor\s+at\s+the\s+crack\s+tip\b", re.IGNORECASE), "stress intensity factor at the crack tip"),
        (re.compile(r"\benergy\s+release\s+velocity\b", re.IGNORECASE), "energy release rate"),
    ]
    for pattern, preferred in term_replacements:
        m = pattern.search(text)
        if m:
            warnings.append(
                Finding(
                    severity="info",
                    category="G1",
                    message=f"Found non-standard mechanics terminology '{m.group(0)}'. Preferred standard term: '{preferred}'.",
                    field="preferred_terminology",
                    context={"found": m.group(0), "preferred": preferred},
                )
            )

    return warnings


def parse_manuscript_sections(text: str) -> List[Dict[str, Any]]:
    """
    Parse sections from Markdown headings or LaTeX section commands.
    """
    sections: List[Dict[str, Any]] = []

    # Check for Markdown headings
    md_matches = list(re.finditer(r"^(#{1,4})\s+(.+?)$", text, re.MULTILINE))
    if md_matches:
        for i, match in enumerate(md_matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = md_matches[i + 1].start() if i + 1 < len(md_matches) else len(text)
            sec_type = _classify_section_title(title)
            sections.append({
                "title": title,
                "level": level,
                "section_type": sec_type,
                "start": start,
                "end": end,
                "content_length": end - start,
            })
        return sections

    # Check for LaTeX section headings
    tex_matches = list(re.finditer(r"\\(section|subsection|subsubsection)\*?\{([^}]+)\}", text))
    if tex_matches:
        for i, match in enumerate(tex_matches):
            cmd = match.group(1)
            title = match.group(2).strip()
            level = 1 if cmd == "section" else (2 if cmd == "subsection" else 3)
            start = match.start()
            end = tex_matches[i + 1].start() if i + 1 < len(tex_matches) else len(text)
            sec_type = _classify_section_title(title)
            sections.append({
                "title": title,
                "level": level,
                "section_type": sec_type,
                "start": start,
                "end": end,
                "content_length": end - start,
            })
        return sections

    sections.append({
        "title": "Full Manuscript",
        "level": 1,
        "section_type": "full_body",
        "start": 0,
        "end": len(text),
        "content_length": len(text),
    })
    return sections


def _classify_section_title(title: str) -> str:
    """Classify section title into standard academic mechanics section types."""
    t = title.lower()
    if "abstract" in t:
        return "abstract"
    elif "intro" in t:
        return "introduction"
    elif any(k in t for k in ["formulation", "model", "governing", "theory", "method"]):
        return "formulation"
    elif any(k in t for k in ["validation", "verification", "benchmark", "convergence"]):
        return "validation"
    elif any(k in t for k in ["result", "simulation", "numerical"]):
        return "results"
    elif any(k in t for k in ["discussion", "mechanism"]):
        return "discussion"
    elif any(k in t for k in ["conclusion", "summary"]):
        return "conclusion"
    return "other"


def analyze_manuscript(
    text: str,
    routing: Optional[Dict[str, Any]] = None,
    conventions: Optional[Union[Dict[str, Any], ConventionRegistry]] = None,
) -> Dict[str, Any]:
    """
    Comprehensive manuscript analysis for academic mechanics papers.
    """
    if conventions is None:
        conv_reg = ConventionRegistry()
    elif isinstance(conventions, dict):
        conv_reg = ConventionRegistry.from_dict(conventions)
    else:
        conv_reg = conventions

    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    sections = parse_manuscript_sections(text)
    protected_zones = extract_protected_zones(text)
    cliches = detect_cliches(text, protected_zones)
    warnings = detect_notation_warnings(text, conv_reg)

    words = len(text.split())
    math_zones = [z for z in protected_zones if z.zone_type.startswith("math")]

    return {
        "source_hash": source_hash,
        "routing": routing or {"paper_type": "research", "language": "en"},
        "statistics": {
            "char_count": len(text),
            "word_count": words,
            "section_count": len(sections),
            "protected_zones_count": len(protected_zones),
            "math_zones_count": len(math_zones),
            "cliches_count": len(cliches),
            "notation_warnings_count": len(warnings),
        },
        "sections": sections,
        "protected_zones": [z.to_dict() for z in protected_zones],
        "cliches": cliches,
        "notation_warnings": [w.to_dict() for w in warnings],
    }


def prepare_polish_request(
    manuscript_analysis: Dict[str, Any],
    style_options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Prepare a structured, constrained polish task package for host LLM execution.
    If no host LLM is connected, status is explicitly marked 'needs_authoring'.
    """
    opts = style_options or {}
    voice = opts.get("voice", "active_mechanics")
    conciseness = opts.get("conciseness", "high")

    return {
        "status": "needs_authoring",
        "task_name": "mechanics_paper_polishing",
        "source_hash": manuscript_analysis["source_hash"],
        "statistics": manuscript_analysis.get("statistics", {}),
        "style_guidelines": {
            "voice": voice,
            "conciseness": conciseness,
            "principles": [
                "Strictly preserve all math equations, variables, and physical units without modification.",
                "Replace passive AI clichés with direct, active physical phrasing (subject + action + condition + observable).",
                "Ensure stress intensity factors, crack opening displacements, and shear strain notations are unambiguous.",
                "Do not upgrade numerical approximations or finite element simulations to 'exact solutions' or 'analytical proofs'.",
            ],
            "forbidden_cliches": [c["word"] for c in AI_CLICHE_RULES[:10]],
        },
        "detected_cliches": manuscript_analysis.get("cliches", []),
        "notation_warnings": manuscript_analysis.get("notation_warnings", []),
        "protected_zones_summary": {
            "total_zones": len(manuscript_analysis.get("protected_zones", [])),
            "note": "Mathematical expressions and citations are locked by SHA-256 integrity hashes.",
        },
        "output_schema_expected": {
            "proposals": [
                {
                    "edit_id": "string",
                    "start": "int",
                    "end": "int",
                    "original_text": "string",
                    "replacement": "string",
                    "category": "style | clarity | notation",
                    "reason": "string",
                }
            ]
        },
    }


def validate_edits(
    before: str,
    proposals: List[Dict[str, Any]],
    constraints: Optional[Dict[str, Any]] = None,
) -> List[Finding]:
    """
    Validate proposed text edits before application:
    - Asserts original text substring matches before[start:end]
    - Asserts no protected zone (math, citation, code block) is altered or swallowed
    - Checks for overlapping edit proposals
    - Checks that replacements do not introduce new prohibited clichés
    - Asserts no unauthorized scientific upgrades (e.g. 'exact solution' or 'proved analytically')
    """
    findings: List[Finding] = []
    protected_zones = extract_protected_zones(before)

    sorted_props = sorted(proposals, key=lambda p: int(p.get("start", 0)))

    prev_end = -1
    for p in sorted_props:
        start = int(p.get("start", -1))
        end = int(p.get("end", -1))
        edit_id = p.get("edit_id", "unknown")
        orig = p.get("original_text", "")
        repl = p.get("replacement", "")

        if start < 0 or end > len(before) or start >= end:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message=f"Proposal {edit_id} has invalid text span [{start}, {end}].",
                    field="proposals",
                    context={"edit_id": edit_id, "start": start, "end": end},
                )
            )
            continue

        if start < prev_end:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message=f"Proposal {edit_id} overlaps with a preceding proposal at position {start} < {prev_end}.",
                    field="proposals",
                    context={"edit_id": edit_id, "start": start, "prev_end": prev_end},
                )
            )
        prev_end = max(prev_end, end)

        actual_slice = before[start:end]
        if actual_slice != orig:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message=f"Proposal {edit_id} original_text mismatch: expected '{orig}', found '{actual_slice}'.",
                    field="original_text",
                    context={"edit_id": edit_id, "expected": orig, "actual": actual_slice},
                )
            )

        for z in protected_zones:
            if not (end <= z.start or start >= z.end):
                if orig != repl:
                    findings.append(
                        Finding(
                            severity="critical",
                            category="G1",
                            message=f"Proposal {edit_id} attempts to modify protected {z.zone_type} zone ({z.id}): '{z.content}'. Math and citations are locked.",
                            field="protected_zones",
                            context={"edit_id": edit_id, "zone_id": z.id, "zone_content": z.content},
                        )
                    )

        for rule in AI_CLICHE_RULES:
            if rule["pattern"].search(repl):
                findings.append(
                    Finding(
                        severity="warning",
                        category="G1",
                        message=f"Proposal {edit_id} introduces prohibited AI cliché '{rule['word']}' in replacement: '{repl}'.",
                        field="replacement",
                        context={"edit_id": edit_id, "word": rule["word"]},
                    )
                )

        if re.search(r"\b(?:exact\s+solution|proves\s+analytically|always\s+valid|unprecedented)\b", repl, re.IGNORECASE):
            if not re.search(r"\b(?:exact\s+solution|proves\s+analytically|always\s+valid|unprecedented)\b", orig, re.IGNORECASE):
                findings.append(
                    Finding(
                        severity="critical",
                        category="G5",
                        message=f"Proposal {edit_id} introduces unverified scientific certainty/exactness claim into replacement: '{repl}'.",
                        field="replacement",
                        context={"edit_id": edit_id},
                    )
                )

    return findings


def apply_edits(
    before: str,
    proposals: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Safely apply non-overlapping, validated edit proposals to the manuscript text.
    Returns:
        (modified_text, diff_records)
    """
    findings = validate_edits(before, proposals)
    critical_errors = [f for f in findings if f.severity == "critical"]
    if critical_errors:
        raise ValueError(
            f"Cannot apply edits due to {len(critical_errors)} critical integrity violations: "
            + "; ".join(f.message for f in critical_errors[:3])
        )

    sorted_proposals = sorted(proposals, key=lambda p: int(p["start"]), reverse=True)

    text_chars = list(before)
    diff_records: List[Dict[str, Any]] = []

    for p in sorted_proposals:
        start = int(p["start"])
        end = int(p["end"])
        orig = p["original_text"]
        repl = p["replacement"]
        edit_id = p.get("edit_id", "unknown")

        text_chars[start:end] = list(repl)

        diff_records.append({
            "edit_id": edit_id,
            "start": start,
            "end": end,
            "original_text": orig,
            "replacement": repl,
            "category": p.get("category", "style"),
            "reason": p.get("reason", ""),
            "applied": True,
        })

    modified_text = "".join(text_chars)
    diff_records.reverse()

    return modified_text, diff_records
