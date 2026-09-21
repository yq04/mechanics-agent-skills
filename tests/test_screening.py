"""
Unit tests for 5-Dimensional Mechanics Rubric screening and PRISMA counter.
"""

import pytest

from mechanics_skills.models import PaperRecord
from mechanics_skills.screening import (
    screen_paper,
    screen_papers,
    PRISMACounter,
    DimensionScore,
    ScreeningResult,
)


def test_screen_paper_priority():
    """Papers addressing TI media, penny cracks, Fabrikant potentials, Kachanov method, SIF/COD should get top score."""
    paper = PaperRecord(
        title="Interacting penny-shaped cracks in a transversely isotropic elastic body",
        abstract=(
            "We formulate the 3D boundary value problem of multiple coplanar penny-shaped cracks "
            "in transversely isotropic media using Fabrikant potential representation. "
            "The Kachanov self-consistent traction method is employed to obtain the exact transmission matrix. "
            "Closed-form stress intensity factor K_I and crack opening displacement COD are derived."
        ),
        year=2021,
        doi="10.1016/sample.priority"
    )

    res = screen_paper(paper)
    assert res.total_score >= 8
    assert res.category == "Included / Priority"
    assert res.exclusion_rationale is None
    # Check dimensions
    assert res.breakdown["constitutive"].score == 2
    assert res.breakdown["geometry"].score == 2
    assert res.breakdown["method"].score == 2
    assert res.breakdown["interaction"].score == 2
    assert res.breakdown["fields"].score == 2


def test_screen_paper_contextual():
    """Papers with partial coverage (e.g. isotropic, single crack, numerical BEM) get Contextual/Background."""
    paper = PaperRecord(
        title="Boundary element analysis of a 2D crack in isotropic elasticity",
        abstract=(
            "A standard boundary element method (BEM) is implemented to compute stress concentration "
            "around a single slit in an isotropic linear elastic plate under tension."
        ),
        year=2018,
        doi="10.1016/sample.contextual"
    )

    res = screen_paper(paper)
    assert 4 <= res.total_score <= 6
    assert res.category == "Contextual / Background"
    assert res.exclusion_rationale is None


def test_screen_paper_biomedical_exclusion():
    """Biomedical or orthopedic papers should be immediately excluded with explicit rationale."""
    paper = PaperRecord(
        title="Clinical evaluation of femoral bone fracture healing after orthopedic implant",
        abstract="Patient cohorts with distal femur bone fracture were monitored for biological soft tissue repair.",
        year=2022,
        doi="10.1016/sample.biomed"
    )

    res = screen_paper(paper)
    assert res.total_score == 0
    assert res.category == "Excluded"
    assert res.exclusion_rationale is not None
    assert "biomedical/clinical" in res.exclusion_rationale.lower()


def test_screen_paper_low_score_exclusion():
    """Generic or weak papers without solid mechanics rigor should be excluded with missing dimensions logged."""
    paper = PaperRecord(
        title="Overview of mechanical properties of plastics",
        abstract="General discussion on density and commercial usage of everyday polymers.",
        year=2019,
        doi="10.1016/sample.generic"
    )

    res = screen_paper(paper)
    assert res.total_score <= 3
    assert res.category == "Excluded"
    assert "Insufficient mechanics rubric score" in res.exclusion_rationale


def test_prisma_counter_flow():
    """PRISMACounter must maintain flow balance across stages."""
    counter = PRISMACounter()
    counter.record_identification(50)
    assert counter.identified == 50
    assert counter.screened == 50

    counter.record_deduplication(10)
    assert counter.duplicates_removed == 10
    assert counter.screened == 40  # 50 - 10

    # Create dummy screening results
    p_high = PaperRecord(
        title="Penny crack in TI medium with Fabrikant potential",
        abstract="Explicit SIF and COD calculated via Kachanov superposition.",
        year=2020
    )
    p_med = PaperRecord(
        title="Isotropic crack BEM study",
        abstract="Stress field around a crack.",
        year=2020
    )
    p_exc = PaperRecord(
        title="Distal femur bone fracture repair in clinical patients",
        abstract="Orthopedic clinical implant study.",
        year=2020
    )

    screen_papers([p_high, p_med, p_exc], counter=counter)
    assert counter.screened_excluded >= 1
    assert counter.assessed_eligibility >= 2
    assert counter.included >= 1

    # Record full-text exclusion
    counter.record_eligibility_exclusion("Missing explicit mathematical potentials")
    assert counter.eligibility_excluded == 1

    summary_text = counter.summary()
    assert "PRISMA Flow Summary:" in summary_text
    assert "Duplicates Removed: 10" in summary_text
