"""
mechanics-agent-skills
======================
Evidence-anchored research tools for solid mechanics, fracture mechanics, and elasticity.
"""

__version__ = "3.1.0"

from mechanics_skills.errors import (
    MechanicsError,
    ProviderError,
    RateLimitError,
    ParsingError,
)
from mechanics_skills.models import (
    Author,
    CitationEdge,
    EvidenceCard,
    OAResult,
    PaperRecord,
)
from mechanics_skills.integrity import (
    Finding,
    ConventionRegistry,
    DataProvenance,
    audit_data_provenance,
    create_data_provenance,
    check_constitutive_admissibility,
    check_sif_normalization,
    run_integrity_pipeline,
)
from mechanics_skills.figure import (
    FigureSpec,
    validate_figure_spec,
    render_figure,
)
from mechanics_skills.workflow import (
    MechanicsWorkflow,
    run_workflow,
    resume_workflow,
    STAGES,
    ARTIFACT_DAG,
)

__all__ = [
    "__version__",
    "MechanicsError",
    "ProviderError",
    "RateLimitError",
    "ParsingError",
    "Author",
    "CitationEdge",
    "EvidenceCard",
    "OAResult",
    "PaperRecord",
    "Finding",
    "ConventionRegistry",
    "DataProvenance",
    "audit_data_provenance",
    "create_data_provenance",
    "check_constitutive_admissibility",
    "check_sif_normalization",
    "run_integrity_pipeline",
    "FigureSpec",
    "validate_figure_spec",
    "render_figure",
    "MechanicsWorkflow",
    "run_workflow",
    "resume_workflow",
    "STAGES",
    "ARTIFACT_DAG",
]
