"""
Unit tests for MechanicsWorkflow engine, manifest persistence, DAG dependencies,
resume caching, and CLI dispatchers.
"""

import json
from pathlib import Path
import pytest
import shutil

from mechanics_skills.workflow import (
    MechanicsWorkflow,
    run_workflow,
    resume_workflow,
    STAGES,
    ARTIFACT_DAG,
)
from mechanics_skills.cli import workflow_cli, integrity_cli


@pytest.fixture
def temp_wf_dir(tmp_path):
    d = tmp_path / "wf_run"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def test_workflow_initialization(temp_wf_dir):
    wf = MechanicsWorkflow(output_dir=temp_wf_dir)
    assert len(STAGES) == 6
    assert STAGES[0] == "literature_review"
    assert STAGES[-1] == "integrity_audit"
    assert "evidence_extraction" in ARTIFACT_DAG["paper_polishing"]
    assert "paper_polishing" in ARTIFACT_DAG["peer_review"]
    assert wf.manifest_path.name == "workflow.manifest.json"
    assert wf.compat_manifest_path.name == "manifest.json"


def test_workflow_run_step_execution_and_persistence(temp_wf_dir):
    config = {
        "run_id": "test-run-101",
        "topic": "Coplanar cracks in transversely isotropic elasticity",
        "offline": True,
        "journal": "jmps",
        "options": {
            "sif_val": 1.15,
            "baseline_val": 1.0,
        },
    }

    manifest = run_workflow(config_path=config, output_dir=temp_wf_dir, offline=True)
    assert manifest["status"] in ("completed", "needs_input")
    assert manifest["run_id"] == "test-run-101"

    # Verify manifest file persistence
    assert (temp_wf_dir / "workflow.manifest.json").is_file()
    assert (temp_wf_dir / "manifest.json").is_file()

    # Verify stage statuses
    stages = manifest["stages"]
    for s in STAGES:
        assert stages[s]["status"] == "completed"
        assert len(stages[s]["output_hashes"]) > 0

    # Verify key directory artifacts exist
    assert (temp_wf_dir / "literature" / "papers.json").is_file()
    assert (temp_wf_dir / "literature" / "references.bib").is_file()
    assert (temp_wf_dir / "literature" / "prisma_flowchart.mmd").is_file()
    assert (temp_wf_dir / "evidence" / "evidence_cards.json").is_file()
    assert (temp_wf_dir / "evidence" / "evidence_matrix.md").is_file()
    assert (temp_wf_dir / "figures" / "spec.json").is_file()
    assert (temp_wf_dir / "manuscript" / "original_manuscript.md").is_file()
    assert (temp_wf_dir / "manuscript" / "analysis.json").is_file()
    assert (temp_wf_dir / "reviews" / "review_report.md").is_file()
    assert (temp_wf_dir / "integrity" / "integrity_report.json").is_file()
    assert (temp_wf_dir / "handoff" / "handoff_memo.md").is_file()


def test_workflow_resume_on_unchanged_hashes(temp_wf_dir):
    config = {
        "run_id": "test-resume-001",
        "topic": "Mode I SIF for interacting crack arrays",
        "offline": True,
    }

    res1 = run_workflow(config_path=config, output_dir=temp_wf_dir, offline=True)
    t_lit1 = res1["stages"]["literature_review"]["completed_at"]
    t_fig1 = res1["stages"]["figure_generation"]["completed_at"]
    t_int1 = res1["stages"]["integrity_audit"]["completed_at"]

    # Resume without changing any inputs
    res2 = resume_workflow(manifest_path=temp_wf_dir / "workflow.manifest.json")
    t_lit2 = res2["stages"]["literature_review"]["completed_at"]
    t_fig2 = res2["stages"]["figure_generation"]["completed_at"]
    t_int2 = res2["stages"]["integrity_audit"]["completed_at"]

    assert t_lit1 == t_lit2
    assert t_fig1 == t_fig2
    assert t_int1 == t_int2


def test_workflow_resume_reruns_modified_stage(temp_wf_dir):
    config = {
        "run_id": "test-resume-mod",
        "topic": "Collinear cracks",
        "offline": True,
        "figure_spec": {
            "template": "sif_curve",
            "title": "Initial Curve",
            "data": {
                "curves": [{"label": "Curve 1", "x": [0, 1], "y": [1.0, 1.2]}],
                "baseline": 1.0,
            },
        },
    }

    res1 = run_workflow(config_path=config, output_dir=temp_wf_dir, offline=True)
    t_lit1 = res1["stages"]["literature_review"]["completed_at"]
    t_fig1 = res1["stages"]["figure_generation"]["completed_at"]

    # Modify figure_spec in the manifest configuration
    m_path = temp_wf_dir / "workflow.manifest.json"
    manifest_data = json.loads(m_path.read_text(encoding="utf-8"))
    manifest_data["config"]["figure_spec"]["data"]["curves"].append({
        "label": "Curve 2", "x": [0, 1], "y": [1.1, 1.3]
    })
    m_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    res2 = resume_workflow(manifest_path=m_path)
    t_lit2 = res2["stages"]["literature_review"]["completed_at"]
    t_fig2 = res2["stages"]["figure_generation"]["completed_at"]

    # Literature review was unchanged, but figure_generation was modified and re-run
    assert t_lit1 == t_lit2
    assert t_fig1 != t_fig2


def test_workflow_cli_run_resume_status(temp_wf_dir):
    run_cfg_path = temp_wf_dir / "run.json"
    run_cfg_path.write_text(json.dumps({
        "run_id": "cli-test-run",
        "topic": "Crack tip fields",
        "offline": True,
    }), encoding="utf-8")

    out_sub = temp_wf_dir / "artifacts_out"

    # Test run
    ret_run = workflow_cli(["run", str(run_cfg_path), "--output-dir", str(out_sub), "--offline", "--format", "json"])
    assert ret_run in (0, 2)
    assert (out_sub / "workflow.manifest.json").is_file()

    # Test status
    ret_status = workflow_cli(["status", str(out_sub / "workflow.manifest.json"), "--format", "json"])
    assert ret_status == 0

    # Test resume
    ret_resume = workflow_cli(["resume", str(out_sub / "manifest.json"), "--format", "json"])
    assert ret_resume in (0, 2)


def test_integrity_cli_check():
    # Run integrity check on run.json
    ret = integrity_cli(["check", "examples/workflow/run.json", "--format", "json"])
    assert ret in (0, 2)
