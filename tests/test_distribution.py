"""
Unit and integration tests for packaging, vendoring, skill bundles, and global sync.
"""

from pathlib import Path
import shutil
import zipfile

from tools.build_skill_bundles import find_skills, build_bundle, EXPECTED_SKILLS, REPO_ROOT
from tools.sync_skills import sync_skills


def test_find_all_expected_skills():
    skills = find_skills(REPO_ROOT)
    skill_names = [s.name for s in skills]
    for expected in EXPECTED_SKILLS:
        assert expected in skill_names


def test_build_bundle_vendors_core_and_creates_zip(tmp_path):
    out_dir = tmp_path / "bundles"
    skill_dir = REPO_ROOT / "mechanics-figure"

    build_bundle(skill_dir, out_dir)

    target_skill = out_dir / "mechanics-figure"
    assert target_skill.is_dir()
    assert (target_skill / "SKILL.md").is_file()
    assert (target_skill / "LICENSE").is_file()
    assert (target_skill / "references" / "figure_templates.md").is_file()

    # Vendor check
    vendor_core = target_skill / "scripts" / "_vendor" / "mechanics_skills"
    assert vendor_core.is_dir()
    assert (vendor_core / "workflow.py").is_file()
    assert (vendor_core / "integrity.py").is_file()
    assert (vendor_core / "figure.py").is_file()

    # Zip check
    zip_path = out_dir / "mechanics-figure.zip"
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert any("SKILL.md" in n for n in names)
        assert any("workflow.py" in n for n in names)


def test_sync_skills_dry_run_and_apply(tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # Create dummy skill in source
    dummy_skill = source_dir / "test-skill"
    dummy_skill.mkdir()
    (dummy_skill / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Dry-run
    res_dry = sync_skills(source_dir, target_dir, dry_run=True)
    assert res_dry["dry_run"] is True
    assert len(res_dry["added_files"]) == 1
    assert not (target_dir / "test-skill" / "SKILL.md").exists()

    # Apply
    res_apply = sync_skills(source_dir, target_dir, dry_run=False)
    assert res_apply["dry_run"] is False
    assert (target_dir / "test-skill" / "SKILL.md").is_file()
