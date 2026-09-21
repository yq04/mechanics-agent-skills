"""
PRISMA-ScR Screening and 5-Dimensional Mechanics Rubric Scoring Engine.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import re

from mechanics_skills.models import PaperRecord


@dataclass
class DimensionScore:
    """Score breakdown for a single dimension in the mechanics rubric."""
    dimension: str
    score: int  # 0 to 2
    matched_keywords: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "matched_keywords": self.matched_keywords,
            "rationale": self.rationale,
        }


@dataclass
class ScreeningResult:
    """Evaluation result of screening a scientific paper."""
    title: str
    doi: Optional[str] = None
    year: Optional[int] = None
    total_score: int = 0
    category: str = "Excluded"  # "Included / Priority", "Contextual / Background", "Excluded"
    breakdown: Dict[str, DimensionScore] = field(default_factory=dict)
    exclusion_rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "doi": self.doi,
            "year": self.year,
            "total_score": self.total_score,
            "category": self.category,
            "breakdown": {k: v.to_dict() for k, v in self.breakdown.items()},
            "exclusion_rationale": self.exclusion_rationale,
        }


@dataclass
class PRISMACounter:
    """
    Tracks review flow metrics conforming to PRISMA-ScR statement.
    Identification -> Screening -> Eligibility -> Included.
    """
    identified: int = 0
    duplicates_removed: int = 0
    screened: int = 0
    screened_excluded: int = 0
    assessed_eligibility: int = 0
    eligibility_excluded: int = 0
    included: int = 0
    exclusion_reasons: Dict[str, int] = field(default_factory=dict)

    def record_identification(self, count: int) -> None:
        self.identified += count
        self.screened = max(0, self.identified - self.duplicates_removed)

    def record_deduplication(self, count: int) -> None:
        self.duplicates_removed += count
        self.screened = max(0, self.identified - self.duplicates_removed)

    def record_screening_result(self, result: ScreeningResult) -> None:
        if result.category == "Excluded":
            self.screened_excluded += 1
            reason = result.exclusion_rationale or "Low mechanics rubric relevance"
            self.exclusion_reasons[reason] = self.exclusion_reasons.get(reason, 0) + 1
        elif result.category in ("Included / Priority", "Contextual / Background"):
            self.assessed_eligibility += 1
            if result.category == "Included / Priority":
                self.included += 1

    def record_eligibility_exclusion(self, reason: str = "Unspecified full-text exclusion") -> None:
        self.eligibility_excluded += 1
        self.exclusion_reasons[reason] = self.exclusion_reasons.get(reason, 0) + 1
        self.included = max(0, self.assessed_eligibility - self.eligibility_excluded)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identified": self.identified,
            "duplicates_removed": self.duplicates_removed,
            "screened": self.screened,
            "screened_excluded": self.screened_excluded,
            "assessed_eligibility": self.assessed_eligibility,
            "eligibility_excluded": self.eligibility_excluded,
            "included": self.included,
            "exclusion_reasons": self.exclusion_reasons,
        }

    def summary(self) -> str:
        lines = [
            "PRISMA Flow Summary:",
            f"  Identified: {self.identified}",
            f"  Duplicates Removed: {self.duplicates_removed}",
            f"  Screened (Title/Abstract): {self.screened}",
            f"  Screened Excluded: {self.screened_excluded}",
            f"  Assessed for Eligibility: {self.assessed_eligibility}",
            f"  Eligibility Excluded: {self.eligibility_excluded}",
            f"  Included in Review: {self.included}",
        ]
        return "\n".join(lines)


# Keyword definitions for the 5-Dimensional Rubric
DIMENSION_CRITERIA = {
    "constitutive": {
        "high": [
            "transversely isotropic", "transverse isotropy", "orthotropic", "anisotropic",
            "piezoelectric", "electro-elastic", "functionally graded", "fgm",
            "hexagonal crystal", "poroelastic", "viscoelastic"
        ],
        "medium": [
            "isotropic", "elastic", "elasticity", "linear elastic", "homogeneous"
        ],
        "exclude": [
            "bone fracture", "femur", "implant", "orthopedic", "soft tissue",
            "blood flow", "cellular", "biological tissue"
        ]
    },
    "geometry": {
        "high": [
            "penny-shaped", "penny crack", "elliptical crack", "coplanar", "non-coplanar",
            "parallel cracks", "interacting cracks", "multiple cracks", "interface crack",
            "bimaterial crack", "inclusion", "eshelby"
        ],
        "medium": [
            "crack", "crack tip", "slit", "notch", "flaw", "defect", "void"
        ],
        "exclude": [
            "nanotube", "quantum dot", "fluid cavity", "cavitation"
        ]
    },
    "method": {
        "high": [
            "potential theory", "fabrikant", "papkovich", "neuber", "muskhelishvili",
            "stroh", "dual integral", "singular integral", "fredholm", "hankel",
            "asymptotic expansion", "mellin", "complex potential"
        ],
        "medium": [
            "boundary element", "bem", "xfem", "collocation", "analytical",
            "semi-analytical", "green function", "weight function"
        ],
        "exclude": [
            "neural network only", "black-box simulation"
        ]
    },
    "interaction": {
        "high": [
            "kachanov", "self-consistent", "superposition", "transmission matrix",
            "interaction matrix", "crack interaction", "multiple defect",
            "shielding", "amplification", "cross-talk", "multipole"
        ],
        "medium": [
            "interaction", "coupled", "coupling", "interference", "proximity"
        ],
        "exclude": []
    },
    "fields": {
        "high": [
            "stress intensity factor", "sif", "mode i", "mode ii", "mode iii",
            "crack opening displacement", "cod", "t-stress", "j-integral",
            "energy release rate", "singular stress field"
        ],
        "medium": [
            "stress field", "displacement field", "stress concentration",
            "compliance", "traction"
        ],
        "exclude": []
    }
}


def evaluate_text_dimension(text: str, dimension: str) -> DimensionScore:
    """Evaluate text content against one rubric dimension."""
    crit = DIMENSION_CRITERIA.get(dimension, {})
    t_lower = text.lower()

    # Check high criteria
    matched_high = [kw for kw in crit.get("high", []) if re.search(r"\b" + re.escape(kw) + r"\b", t_lower)]
    if matched_high:
        return DimensionScore(
            dimension=dimension,
            score=2,
            matched_keywords=matched_high[:5],
            rationale=f"High match on target {dimension} concepts: {', '.join(matched_high[:3])}",
        )

    # Check medium criteria
    matched_med = [kw for kw in crit.get("medium", []) if re.search(r"\b" + re.escape(kw) + r"\b", t_lower)]
    if matched_med:
        return DimensionScore(
            dimension=dimension,
            score=1,
            matched_keywords=matched_med[:5],
            rationale=f"Secondary match on {dimension} concepts: {', '.join(matched_med[:3])}",
        )

    return DimensionScore(
        dimension=dimension,
        score=0,
        matched_keywords=[],
        rationale=f"No relevant {dimension} criteria identified in text.",
    )


def screen_paper(paper: PaperRecord) -> ScreeningResult:
    """
    Screen a single paper using the 5-Dimensional mechanics rubric.
    Evaluates Title and Abstract.
    Scores range from 0 to 10.
    Categorizes into Included / Priority (>=7), Contextual / Background (4-6), or Excluded (0-3).
    """
    full_text = f"{paper.title} {paper.abstract}".strip()
    full_text_lower = full_text.lower()

    # Check explicit exclusion filters first
    for dim, crit in DIMENSION_CRITERIA.items():
        for exc in crit.get("exclude", []):
            if re.search(r"\b" + re.escape(exc) + r"\b", full_text_lower):
                # Check if this is a biomedical / non-mechanics paper
                if any(w in full_text_lower for w in ["bone", "femur", "patient", "clinical", "orthopedic"]):
                    breakdown = {d: DimensionScore(dimension=d, score=0, rationale="Excluded by domain filter") for d in DIMENSION_CRITERIA}
                    return ScreeningResult(
                        title=paper.title,
                        doi=paper.doi,
                        year=paper.year,
                        total_score=0,
                        category="Excluded",
                        breakdown=breakdown,
                        exclusion_rationale=f"Out of scope: biomedical/clinical subject detected ({exc})",
                    )

    breakdown: Dict[str, DimensionScore] = {}
    total_score = 0
    for dim in ["constitutive", "geometry", "method", "interaction", "fields"]:
        d_score = evaluate_text_dimension(full_text, dim)
        breakdown[dim] = d_score
        total_score += d_score.score

    if total_score >= 7:
        category = "Included / Priority"
        exclusion_rationale = None
    elif total_score >= 4:
        category = "Contextual / Background"
        exclusion_rationale = None
    else:
        category = "Excluded"
        missing = [dim for dim, sc in breakdown.items() if sc.score == 0]
        exclusion_rationale = f"Insufficient mechanics rubric score ({total_score}/10). Missing or weak in: {', '.join(missing)}"

    return ScreeningResult(
        title=paper.title,
        doi=paper.doi,
        year=paper.year,
        total_score=total_score,
        category=category,
        breakdown=breakdown,
        exclusion_rationale=exclusion_rationale,
    )


def screen_papers(
    papers: List[PaperRecord], counter: Optional[PRISMACounter] = None
) -> List[ScreeningResult]:
    """Screen multiple papers and optionally update a PRISMACounter."""
    results: List[ScreeningResult] = []
    if counter is not None and counter.screened == 0:
        counter.record_identification(len(papers))
        counter.record_deduplication(0)

    for p in papers:
        res = screen_paper(p)
        results.append(res)
        if counter is not None:
            counter.record_screening_result(res)

    return results
