"""
Lightweight Resumable Workflow Engine for Mechanics Research Lifecycle.
Orchestrates:
1. literature_review -> 2. evidence_extraction -> 3. figure_generation
-> 4. paper_polishing -> 5. peer_review -> 6. integrity_audit.

Supports manifest persistence, SHA-256 DAG hash invalidation,
atomic writes, and resume capability.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union

from mechanics_skills.models import PaperRecord
from mechanics_skills.search import search_literature
from mechanics_skills.screening import screen_papers, PRISMACounter
from mechanics_skills.bibtex import papers_to_bibtex
from mechanics_skills.writing import (
    generate_prisma_mermaid,
    generate_evidence_matrix_markdown,
    generate_review_draft_sections,
)
from mechanics_skills.extraction import (
    extract_evidence_from_pdf,
    extract_evidence_from_text,
    EvidenceCard,
)
from mechanics_skills.figure import validate_figure_spec, render_figure
from mechanics_skills.polishing import (
    analyze_manuscript,
    prepare_polish_request,
    validate_edits,
    apply_edits,
)
from mechanics_skills.reviewer import (
    audit_scientific_soundness,
    prepare_review_package,
    generate_review_report_markdown,
)
from mechanics_skills.integrity import (
    run_integrity_pipeline,
    audit_data_provenance,
    ConventionRegistry,
)


STAGES = [
    "literature_review",
    "evidence_extraction",
    "figure_generation",
    "paper_polishing",
    "peer_review",
    "integrity_audit",
]

ARTIFACT_DAG = {
    "literature_review": [],
    "evidence_extraction": ["literature_review"],
    "figure_generation": ["literature_review"],
    "paper_polishing": ["evidence_extraction"],
    "peer_review": ["paper_polishing", "figure_generation"],
    "integrity_audit": ["peer_review", "figure_generation", "paper_polishing"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash for files or in-memory data."""
    if isinstance(data, (str, Path)) and os.path.isfile(str(data)):
        return hashlib.sha256(Path(str(data)).read_bytes()).hexdigest()
    return audit_data_provenance(data)


def _get_default_papers() -> List[PaperRecord]:
    return [
        PaperRecord(
            title="Exact Potential Solutions for Collinear Cracks in Transversely Isotropic Solids",
            doi="10.1016/j.engfracmech.2021.1001",
            authors=["A. Elastician", "B. Mechanician"],
            year=2021,
            journal="Engineering Fracture Mechanics",
            citations=45,
            abstract="Exact analytical solutions for collinear cracks in transversely isotropic elastic media using Fabrikant potentials to determine Mode I stress intensity factors K_I and COD fields.",
            sources=["crossref", "openalex"],
            extra={"is_synthetic_demo": True},
        ),
        PaperRecord(
            title="Asymptotic Analysis of Crack Interaction Under Remote Tension",
            doi="10.1007/s10409-019-3003",
            authors=["D. Researcher"],
            year=2019,
            journal="Acta Mechanica Sinica",
            citations=28,
            abstract="Boundary element analysis of crack interaction comparing with Kachanov method and analytical Westergaard solutions.",
            sources=["crossref"],
        ),
        PaperRecord(
            title="Bearing Capacity of Foundation Soils under Cyclic Loading",
            doi="10.1016/j.geotech.2020.2002",
            authors=["E. Geologist"],
            year=2020,
            journal="Geotechnique",
            citations=12,
            abstract="Soil mechanics analysis of foundation bearing capacity.",
            sources=["openalex"],
        ),
    ]


def _get_default_figure_spec() -> Dict[str, Any]:
    return {
        "template": "sif_curve",
        "title": "Normalized Mode I Stress Intensity Factor",
        "layout": "single_column",
        "data": {
            "curves": [
                {
                    "label": "Analytical (Fabrikant)",
                    "x": [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
                    "y": [1.02, 1.05, 1.12, 1.25, 1.48, 1.85],
                },
                {
                    "label": "BEM Benchmark",
                    "x": [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
                    "y": [1.01, 1.04, 1.11, 1.24, 1.47, 1.83],
                },
            ],
            "baseline": 1.0,
            "x_label": "Crack spacing ratio $h/a$",
            "y_label": "Normalized SIF $K_I / K_0$",
        },
    }


def _get_default_manuscript() -> str:
    return """# Asymptotic Stress Fields Near Collinear Cracks in Elastic Solids

## Abstract
This work investigates crack-tip stress fields in linear elastic media under mode I loading.
The apparent stress intensity factor is computed for normalized spacing $h/a$.

## 1. Introduction
Understanding defect interactions is essential in structural integrity assessment.
Previous analytical formulations by \\cite{Westergaard1939} provided closed-form potentials for isolated cracks.
Here, we evaluate the shielding mechanisms governing interacting crack arrays.

## 2. Formulation
Consider a series of collinear cracks of length $2a$ separated by distance $h$.
Under remote tensile stress $\\sigma_{\\infty}$, the mode I stress intensity factor satisfies:
$$K_I = \\sigma_{\\infty} \\sqrt{\\pi a} \\cdot f(h/a)$$
where $f(h/a)$ is the geometry correction factor.

## 3. Results and Validation
Numerical validation against analytical benchmark solutions confirms convergence within 0.1%.
Independent validation confirms strict boundary condition satisfaction.
"""


class MechanicsWorkflow:
    """
    Resumable end-to-end workflow runner for mechanics research pipelines.
    """

    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / "workflow.manifest.json"
        self.compat_manifest_path = self.output_dir / "manifest.json"
        self.manifest: Dict[str, Any] = {}

    def _init_manifest(self, config: Dict[str, Any], config_path: Optional[str] = None) -> Dict[str, Any]:
        run_id = config.get("run_id") or f"run-{int(datetime.now().timestamp())}"
        config_hash = _compute_hash(config)

        stages_dict = {}
        for s in STAGES:
            stages_dict[s] = {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "input_hashes": {},
                "output_hashes": {},
                "artifacts": [],
                "metadata": {},
                "warnings": [],
                "pending_tasks": [],
            }

        return {
            "workflow_version": "3.1.0",
            "run_id": run_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "status": "pending",
            "config_path": config_path,
            "config_hash": config_hash,
            "config": config,
            "output_dir": str(self.output_dir.resolve()),
            "stages": stages_dict,
            "artifact_dag": ARTIFACT_DAG,
            "decisions": [],
            "warnings": [],
            "pending_tasks": [],
            "handoff": {},
        }

    def _save_manifest(self) -> None:
        self.manifest["updated_at"] = _now_iso()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.manifest_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self.manifest_path)
        compat_tmp = self.compat_manifest_path.with_suffix(".tmp")
        shutil.copy2(self.manifest_path, compat_tmp)
        compat_tmp.replace(self.compat_manifest_path)

    def run(
        self,
        config: Union[str, Path, Dict[str, Any]],
        offline: bool = False,
    ) -> Dict[str, Any]:
        """Execute all stages of the workflow from configuration."""
        config_path_str = None
        if isinstance(config, (str, Path)):
            config_path_str = str(Path(config).resolve())
            with open(config, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = dict(config)

        if offline or cfg.get("offline", False):
            cfg["offline"] = True

        self.manifest = self._init_manifest(cfg, config_path=config_path_str)
        self.manifest["status"] = "running"
        self._save_manifest()

        for stage_name in STAGES:
            stage_info = self.manifest["stages"][stage_name]
            stage_info["status"] = "running"
            stage_info["started_at"] = _now_iso()
            self._save_manifest()

            try:
                out_hashes, artifacts, meta, warns, tasks = self._run_stage(stage_name, cfg)
                stage_info["output_hashes"] = out_hashes
                stage_info["artifacts"] = artifacts
                stage_info["metadata"] = meta
                stage_info["warnings"] = warns
                stage_info["pending_tasks"] = tasks
                stage_info["completed_at"] = _now_iso()
                stage_info["status"] = "completed"

                if warns:
                    self.manifest["warnings"].extend(warns)
                if tasks:
                    self.manifest["pending_tasks"].extend(tasks)

                self.manifest["decisions"].append({
                    "stage": stage_name,
                    "action": f"Executed {stage_name} successfully",
                    "timestamp": _now_iso(),
                })

            except Exception as e:
                stage_info["status"] = "failed"
                stage_info["completed_at"] = _now_iso()
                stage_info["warnings"].append(str(e))
                self.manifest["status"] = "failed"
                self._save_manifest()
                raise

            self._save_manifest()

        self._finalize_workflow()
        return self.manifest

    def resume(self) -> Dict[str, Any]:
        """
        Inspect stage hashes and dependencies, re-running only stale, uncompleted,
        or modified stages.
        """
        if not self.manifest:
            manifest_target = self.manifest_path if self.manifest_path.exists() else self.compat_manifest_path
            if not manifest_target.exists():
                raise FileNotFoundError(f"No manifest found in {self.output_dir}")
            with open(manifest_target, "r", encoding="utf-8") as f:
                self.manifest = json.load(f)

        cfg = self.manifest.get("config", {})
        resumed_stages = []

        for stage_name in STAGES:
            stage_info = self.manifest["stages"][stage_name]
            current_inputs = self._gather_stage_inputs(stage_name, cfg)
            current_input_hashes = {k: _compute_hash(v) for k, v in current_inputs.items()}

            hashes_match = (
                stage_info.get("status") == "completed"
                and stage_info.get("input_hashes") == current_input_hashes
            )

            upstream_rerun = any(dep in resumed_stages for dep in ARTIFACT_DAG.get(stage_name, []))

            if hashes_match and not upstream_rerun:
                continue

            stage_info["status"] = "running"
            stage_info["started_at"] = _now_iso()
            stage_info["input_hashes"] = current_input_hashes
            self._save_manifest()

            out_hashes, artifacts, meta, warns, tasks = self._run_stage(stage_name, cfg)
            stage_info["output_hashes"] = out_hashes
            stage_info["artifacts"] = artifacts
            stage_info["metadata"] = meta
            stage_info["warnings"] = warns
            stage_info["pending_tasks"] = tasks
            stage_info["completed_at"] = _now_iso()
            stage_info["status"] = "completed"

            resumed_stages.append(stage_name)
            self.manifest["decisions"].append({
                "stage": stage_name,
                "action": f"Resumed and re-executed {stage_name}",
                "timestamp": _now_iso(),
            })
            self._save_manifest()

        self._finalize_workflow()
        return self.manifest

    def _gather_stage_inputs(self, stage_name: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Collect input files or data keys for a stage to compute input hashes."""
        inputs = {}
        if stage_name == "literature_review":
            inputs["topic"] = cfg.get("topic") or cfg.get("query") or "collinear cracks"
            inputs["offline"] = cfg.get("offline", False)
            if "papers" in cfg:
                inputs["papers"] = cfg["papers"]

        elif stage_name == "evidence_extraction":
            lit_dir = self.output_dir / "literature"
            inc_file = lit_dir / "included_papers.json"
            if inc_file.is_file():
                inputs["included_papers"] = str(inc_file)
            if "evidence_sources" in cfg:
                inputs["evidence_sources"] = cfg["evidence_sources"]

        elif stage_name == "figure_generation":
            if "figure_spec_path" in cfg and os.path.isfile(cfg["figure_spec_path"]):
                inputs["spec_file"] = cfg["figure_spec_path"]
            elif "figure_spec" in cfg:
                inputs["spec_data"] = cfg["figure_spec"]

        elif stage_name == "paper_polishing":
            if "manuscript_path" in cfg and os.path.isfile(cfg["manuscript_path"]):
                inputs["manuscript"] = cfg["manuscript_path"]
            elif "manuscript" in cfg:
                inputs["manuscript_data"] = cfg["manuscript"]
            if "conventions_path" in cfg and os.path.isfile(cfg["conventions_path"]):
                inputs["conventions"] = cfg["conventions_path"]
            elif "conventions" in cfg:
                inputs["conventions_data"] = cfg["conventions"]
            if "proposals" in cfg:
                inputs["proposals"] = cfg["proposals"]
            elif "proposals_path" in cfg and os.path.isfile(cfg["proposals_path"]):
                inputs["proposals"] = cfg["proposals_path"]

        elif stage_name == "peer_review":
            ms_dir = self.output_dir / "manuscript"
            pol_ms = ms_dir / "polished_manuscript.md"
            orig_ms = ms_dir / "original_manuscript.md"
            if pol_ms.is_file():
                inputs["manuscript"] = str(pol_ms)
            elif orig_ms.is_file():
                inputs["manuscript"] = str(orig_ms)
            inputs["journal"] = cfg.get("journal", "jmps")

        elif stage_name == "integrity_audit":
            ms_dir = self.output_dir / "manuscript"
            pol_ms = ms_dir / "polished_manuscript.md"
            orig_ms = ms_dir / "original_manuscript.md"
            if pol_ms.is_file():
                inputs["manuscript"] = str(pol_ms)
            elif orig_ms.is_file():
                inputs["manuscript"] = str(orig_ms)
            fig_manifest = self.output_dir / "figures" / "figure.manifest.json"
            if fig_manifest.is_file():
                inputs["figure_manifest"] = str(fig_manifest)
            if "options" in cfg:
                inputs["options"] = cfg["options"]

        return inputs

    def _run_stage(
        self, stage_name: str, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        """Dispatch stage execution."""
        inputs = self._gather_stage_inputs(stage_name, cfg)
        input_hashes = {k: _compute_hash(v) for k, v in inputs.items()}
        self.manifest["stages"][stage_name]["input_hashes"] = input_hashes

        if stage_name == "literature_review":
            return self._run_literature_review(cfg)
        elif stage_name == "evidence_extraction":
            return self._run_evidence_extraction(cfg)
        elif stage_name == "figure_generation":
            return self._run_figure_generation(cfg)
        elif stage_name == "paper_polishing":
            return self._run_paper_polishing(cfg)
        elif stage_name == "peer_review":
            return self._run_peer_review(cfg)
        elif stage_name == "integrity_audit":
            return self._run_integrity_audit(cfg)
        else:
            raise ValueError(f"Unknown stage: {stage_name}")

    def _run_literature_review(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        out_dir = self.output_dir / "literature"
        out_dir.mkdir(parents=True, exist_ok=True)
        query = cfg.get("topic") or cfg.get("query") or "collinear cracks in elastic solids"
        offline = cfg.get("offline", False)
        sources = cfg.get("sources", ["crossref", "openalex"])

        if "papers" in cfg and cfg["papers"]:
            papers = [
                PaperRecord.from_dict(p) if isinstance(p, dict) else p
                for p in cfg["papers"]
            ]
        elif offline:
            papers = _get_default_papers()
        else:
            papers = search_literature(query=query, sources=sources, limit_per_source=cfg.get("limit", 10), silent=True)

        counter = PRISMACounter(identified=len(papers))
        screening_results = screen_papers(papers, counter=counter)
        included_papers = [
            p for p, sr in zip(papers, screening_results)
            if sr.category in ("Included / Priority", "Contextual / Background")
        ]

        papers_file = out_dir / "papers.json"
        papers_file.write_text(json.dumps([p.to_dict() for p in papers], indent=2, ensure_ascii=False), encoding="utf-8")

        inc_file = out_dir / "included_papers.json"
        inc_file.write_text(json.dumps([p.to_dict() for p in included_papers], indent=2, ensure_ascii=False), encoding="utf-8")

        bib_file = out_dir / "references.bib"
        bib_file.write_text(papers_to_bibtex(included_papers), encoding="utf-8")

        flow_file = out_dir / "prisma_flowchart.mmd"
        flow_file.write_text(generate_prisma_mermaid(counter), encoding="utf-8")

        summary_file = out_dir / "screening_summary.json"
        summary_data = {
            "query": query,
            "identified": counter.identified,
            "screened": counter.screened,
            "included": counter.included,
            "excluded": counter.screened_excluded,
        }
        summary_file.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

        artifacts = [str(papers_file), str(inc_file), str(bib_file), str(flow_file), str(summary_file)]
        out_hashes = {str(Path(a).name): _compute_hash(a) for a in artifacts}
        metadata = {"identified_count": len(papers), "included_count": len(included_papers)}
        warnings: List[str] = []
        pending_tasks: List[Dict[str, Any]] = []
        return out_hashes, artifacts, metadata, warnings, pending_tasks

    def _run_evidence_extraction(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        out_dir = self.output_dir / "evidence"
        out_dir.mkdir(parents=True, exist_ok=True)

        lit_inc_file = self.output_dir / "literature" / "included_papers.json"
        papers = []
        if lit_inc_file.is_file():
            papers_data = json.loads(lit_inc_file.read_text(encoding="utf-8"))
            papers = [PaperRecord.from_dict(p) for p in papers_data]
        elif "papers" in cfg:
            papers = [PaperRecord.from_dict(p) if isinstance(p, dict) else p for p in cfg["papers"]]
        else:
            papers = _get_default_papers()[:2]

        cards: List[EvidenceCard] = []

        sources = cfg.get("evidence_sources", [])
        for src in sources:
            src_p = Path(src)
            if src_p.is_file():
                if src_p.suffix.lower() == ".pdf":
                    cards.extend(extract_evidence_from_pdf(src_p, document_title=src_p.stem))
                else:
                    cards.extend(extract_evidence_from_text(src_p.read_text(encoding="utf-8", errors="ignore"), document_title=src_p.stem))

        for p in papers:
            text = f"{p.title}\n\n{p.abstract}"
            cards.extend(extract_evidence_from_text(text, document_title=p.title, doi=p.doi, page_number=None, source_type="abstract"))

        cards_file = out_dir / "evidence_cards.json"
        card_dicts = [c.to_dict() for c in cards]
        cards_file.write_text(json.dumps(card_dicts, indent=2, ensure_ascii=False), encoding="utf-8")

        matrix_file = out_dir / "evidence_matrix.md"
        matrix_file.write_text(generate_evidence_matrix_markdown(card_dicts), encoding="utf-8")

        draft_file = out_dir / "review_draft.md"
        draft_file.write_text(generate_review_draft_sections(papers, card_dicts), encoding="utf-8")

        artifacts = [str(cards_file), str(matrix_file), str(draft_file)]
        out_hashes = {str(Path(a).name): _compute_hash(a) for a in artifacts}
        metadata = {"card_count": len(cards), "categories": list(set(c.element_type for c in cards))}
        warnings: List[str] = []
        pending_tasks: List[Dict[str, Any]] = []
        return out_hashes, artifacts, metadata, warnings, pending_tasks

    def _run_figure_generation(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        out_dir = self.output_dir / "figures"
        out_dir.mkdir(parents=True, exist_ok=True)

        if "figure_spec_path" in cfg and os.path.isfile(cfg["figure_spec_path"]):
            spec_data = json.loads(Path(cfg["figure_spec_path"]).read_text(encoding="utf-8"))
        elif "figure_spec" in cfg:
            spec_data = cfg["figure_spec"]
        else:
            spec_data = _get_default_figure_spec()

        findings = validate_figure_spec(spec_data)
        has_critical = any(f.severity == "critical" for f in findings)
        warnings = [f.message for f in findings if f.severity in ("warning", "critical")]

        if has_critical:
            raise ValueError(f"Figure specification critical validation failure: {warnings}")

        fig_manifest = render_figure(spec_data, output_dir=str(out_dir))

        spec_file = out_dir / "spec.json"
        spec_file.write_text(json.dumps(spec_data, indent=2, ensure_ascii=False), encoding="utf-8")

        artifacts = [str(spec_file)]
        if (out_dir / "figure.manifest.json").is_file():
            artifacts.append(str(out_dir / "figure.manifest.json"))
        for export_path in fig_manifest.get("export_files", {}).values():
            if os.path.isfile(export_path):
                artifacts.append(str(export_path))

        out_hashes = {str(Path(a).name): _compute_hash(a) for a in artifacts}
        metadata = {
            "template": fig_manifest.get("template"),
            "layout": fig_manifest.get("layout"),
            "export_files": fig_manifest.get("export_files"),
        }
        pending_tasks: List[Dict[str, Any]] = []
        return out_hashes, artifacts, metadata, warnings, pending_tasks

    def _run_paper_polishing(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        out_dir = self.output_dir / "manuscript"
        out_dir.mkdir(parents=True, exist_ok=True)

        if "manuscript_path" in cfg and os.path.isfile(cfg["manuscript_path"]):
            manuscript_text = Path(cfg["manuscript_path"]).read_text(encoding="utf-8")
        elif "manuscript" in cfg and cfg["manuscript"]:
            manuscript_text = cfg["manuscript"]
        else:
            ev_draft = self.output_dir / "evidence" / "review_draft.md"
            if ev_draft.is_file():
                manuscript_text = ev_draft.read_text(encoding="utf-8")
            else:
                manuscript_text = _get_default_manuscript()

        conv_data = None
        if "conventions_path" in cfg and os.path.isfile(cfg["conventions_path"]):
            conv_data = json.loads(Path(cfg["conventions_path"]).read_text(encoding="utf-8"))
        elif "conventions" in cfg:
            conv_data = cfg["conventions"]

        orig_file = out_dir / "original_manuscript.md"
        orig_file.write_text(manuscript_text, encoding="utf-8")

        analysis = analyze_manuscript(manuscript_text, conventions=conv_data)
        analysis_file = out_dir / "analysis.json"
        analysis_file.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

        req = prepare_polish_request(analysis)
        req_file = out_dir / "polish_request.json"
        req_file.write_text(json.dumps(req, indent=2, ensure_ascii=False), encoding="utf-8")

        artifacts = [str(orig_file), str(analysis_file), str(req_file)]
        warnings = [w["message"] for w in analysis.get("notation_warnings", [])]
        pending_tasks: List[Dict[str, Any]] = []

        proposals = None
        if "proposals" in cfg:
            proposals = cfg["proposals"]
        elif "proposals_path" in cfg and os.path.isfile(cfg["proposals_path"]):
            p_data = json.loads(Path(cfg["proposals_path"]).read_text(encoding="utf-8"))
            proposals = p_data.get("proposals", p_data)

        if proposals:
            val_findings = validate_edits(manuscript_text, proposals)
            has_crit = any(f.severity == "critical" for f in val_findings)
            if has_crit:
                warnings.extend([f.message for f in val_findings if f.severity == "critical"])
            else:
                polished_text, diffs = apply_edits(manuscript_text, proposals)
                pol_file = out_dir / "polished_manuscript.md"
                pol_file.write_text(polished_text, encoding="utf-8")
                diff_file = out_dir / "diff.json"
                diff_file.write_text(json.dumps(diffs, indent=2, ensure_ascii=False), encoding="utf-8")
                artifacts.extend([str(pol_file), str(diff_file)])
        else:
            pol_file = out_dir / "polished_manuscript.md"
            pol_file.write_text(manuscript_text, encoding="utf-8")
            artifacts.append(str(pol_file))
            if analysis["cliches"]:
                pending_tasks.append({
                    "task": "author_polish_proposals",
                    "description": f"Found {len(analysis['cliches'])} cliches. Host model proposals recommended.",
                    "status": "needs_authoring",
                })

        out_hashes = {str(Path(a).name): _compute_hash(a) for a in artifacts}
        metadata = {
            "word_count": analysis["statistics"]["word_count"],
            "cliches_count": analysis["statistics"]["cliches_count"],
            "notation_warnings_count": analysis["statistics"]["notation_warnings_count"],
        }
        return out_hashes, artifacts, metadata, warnings, pending_tasks

    def _run_peer_review(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        out_dir = self.output_dir / "reviews"
        out_dir.mkdir(parents=True, exist_ok=True)

        ms_file = self.output_dir / "manuscript" / "polished_manuscript.md"
        if not ms_file.is_file():
            ms_file = self.output_dir / "manuscript" / "original_manuscript.md"
        manuscript_text = ms_file.read_text(encoding="utf-8") if ms_file.is_file() else _get_default_manuscript()

        journal = cfg.get("journal", "jmps")
        audit_res = audit_scientific_soundness(manuscript_text, journal=journal)
        pkg = prepare_review_package(manuscript_text, journal=journal)
        report_md = generate_review_report_markdown(audit_res)

        audit_file = out_dir / "review_audit.json"
        audit_file.write_text(json.dumps(audit_res, indent=2, ensure_ascii=False), encoding="utf-8")

        pkg_file = out_dir / "review_package.json"
        pkg_file.write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")

        report_file = out_dir / "review_report.md"
        report_file.write_text(report_md, encoding="utf-8")

        artifacts = [str(audit_file), str(pkg_file), str(report_file)]
        out_hashes = {str(Path(a).name): _compute_hash(a) for a in artifacts}
        metadata = {
            "overall_soundness": audit_res["overall_soundness"],
            "major_concerns_count": audit_res["major_concerns_count"],
            "minor_concerns_count": audit_res["minor_concerns_count"],
            "journal": journal,
        }
        warnings = [
            f"{dim_info['name']}: {f.get('observation') or f.get('reasoning') or f.get('message', '')}"
            for dim_info in audit_res["dimensions"].values()
            for f in dim_info.get("findings", [])
            if f.get("severity") in ("major", "critical")
        ]
        pending_tasks: List[Dict[str, Any]] = []
        return out_hashes, artifacts, metadata, warnings, pending_tasks

    def _run_integrity_audit(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, Any], List[str], List[Dict[str, Any]]]:
        out_dir = self.output_dir / "integrity"
        out_dir.mkdir(parents=True, exist_ok=True)

        ms_file = self.output_dir / "manuscript" / "polished_manuscript.md"
        if not ms_file.is_file():
            ms_file = self.output_dir / "manuscript" / "original_manuscript.md"
        manuscript_text = ms_file.read_text(encoding="utf-8") if ms_file.is_file() else _get_default_manuscript()

        data_refs = list(cfg.get("data_refs", []))
        fig_spec_file = self.output_dir / "figures" / "spec.json"
        if fig_spec_file.is_file():
            data_refs.append(str(fig_spec_file))

        conventions = cfg.get("conventions")
        if not conventions and (self.output_dir / "manuscript" / "analysis.json").is_file():
            try:
                a_data = json.loads((self.output_dir / "manuscript" / "analysis.json").read_text(encoding="utf-8"))
                conventions = a_data.get("conventions")
            except Exception:
                pass

        options = cfg.get("options", {})
        integrity_res = run_integrity_pipeline(
            manuscript_text,
            data_refs=data_refs,
            conventions=conventions,
            options=options,
        )

        rep_file = out_dir / "integrity_report.json"
        rep_file.write_text(json.dumps(integrity_res, indent=2, ensure_ascii=False), encoding="utf-8")

        summary_file = out_dir / "integrity_summary.md"
        summary_md = f"""# Scientific Integrity Pipeline Audit Summary

- **Status**: {integrity_res['status'].upper()}
- **Readiness Gate**: {integrity_res['readiness']}
- **Summary**: {integrity_res['summary']}

## Gate-by-Gate Evaluation:
"""
        for g_id, g_info in integrity_res["gates"].items():
            summary_md += f"- **{g_id} ({g_info['name']})**: {g_info['status'].upper()} ({len(g_info['findings'])} findings)\n"

        summary_file.write_text(summary_md, encoding="utf-8")

        artifacts = [str(rep_file), str(summary_file)]
        out_hashes = {str(Path(a).name): _compute_hash(a) for a in artifacts}
        metadata = {
            "status": integrity_res["status"],
            "readiness": integrity_res["readiness"],
            "critical_findings_count": sum(1 for f in integrity_res["all_findings"] if f["severity"] == "critical"),
        }
        warnings = [f["message"] for f in integrity_res["all_findings"] if f["severity"] in ("critical", "warning")]
        pending_tasks: List[Dict[str, Any]] = []
        return out_hashes, artifacts, metadata, warnings, pending_tasks

    def _finalize_workflow(self) -> None:
        """Create handoff memo and calculate final workflow status."""
        handoff_dir = self.output_dir / "handoff"
        handoff_dir.mkdir(parents=True, exist_ok=True)

        stages = self.manifest["stages"]
        all_completed = all(s["status"] == "completed" for s in stages.values())
        any_failed = any(s["status"] == "failed" for s in stages.values())
        any_blocked = stages.get("integrity_audit", {}).get("metadata", {}).get("readiness") == "blocked"

        if any_failed:
            overall = "failed"
        elif any_blocked:
            overall = "blocked"
        elif self.manifest.get("pending_tasks"):
            overall = "needs_input"
        elif all_completed:
            overall = "completed"
        else:
            overall = "partial"

        self.manifest["status"] = overall

        memo_path = handoff_dir / "handoff_memo.md"
        memo_lines = [
            "# Mechanics Research Lifecycle Handoff Memo",
            f"- **Run ID**: {self.manifest['run_id']}",
            f"- **Final Workflow Status**: {overall.upper()}",
            f"- **Generated**: {_now_iso()}",
            "",
            "## Stage Summary",
        ]
        for s_name, s_info in stages.items():
            memo_lines.append(f"- **{s_name}**: status={s_info['status']}, artifacts={len(s_info['artifacts'])}, warnings={len(s_info['warnings'])}")

        memo_lines.append("")
        memo_lines.append("## Decisions & Handoff Actions")
        for dec in self.manifest["decisions"]:
            memo_lines.append(f"- [{dec['timestamp'][:19]}] {dec['action']}")

        if self.manifest["pending_tasks"]:
            memo_lines.append("")
            memo_lines.append("## Pending Author Tasks (needs_input)")
            for pt in self.manifest["pending_tasks"]:
                memo_lines.append(f"- **{pt.get('task')}**: {pt.get('description', '')}")

        memo_content = "\n".join(memo_lines) + "\n"
        memo_path.write_text(memo_content, encoding="utf-8")

        self.manifest["handoff"] = {
            "memo_path": str(memo_path),
            "overall_status": overall,
            "decisions_count": len(self.manifest["decisions"]),
            "warnings_count": len(self.manifest["warnings"]),
            "pending_tasks_count": len(self.manifest["pending_tasks"]),
        }
        self._save_manifest()


def run_workflow(
    config_path: Union[str, Path, Dict[str, Any]],
    output_dir: Union[str, Path],
    offline: bool = False,
) -> Dict[str, Any]:
    """Execute complete mechanics research workflow."""
    wf = MechanicsWorkflow(output_dir=output_dir)
    return wf.run(config=config_path, offline=offline)


def resume_workflow(manifest_path: Union[str, Path]) -> Dict[str, Any]:
    """Resume execution of a previously initiated workflow run."""
    p = Path(manifest_path)
    if p.is_dir():
        out_dir = p
    else:
        out_dir = p.parent

    wf = MechanicsWorkflow(output_dir=out_dir)
    return wf.resume()
