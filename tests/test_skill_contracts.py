"""
Contract tests for all 6 mechanics agent skills.
Validates SKILL.md frontmatter, documentation structure, scripts, and vendored imports.
"""

from pathlib import Path
import re
from tools.build_skill_bundles import EXPECTED_SKILLS, REPO_ROOT


def test_skill_contracts_all_six():
    for skill_name in EXPECTED_SKILLS:
        skill_dir = REPO_ROOT / skill_name
        assert skill_dir.is_dir(), f"Missing skill directory: {skill_name}"

        # 1. Check SKILL.md
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.is_file(), f"Missing SKILL.md in {skill_name}"
        content = skill_md.read_text(encoding="utf-8")

        # 2. Check frontmatter
        assert content.startswith("---"), f"{skill_name} SKILL.md must start with YAML frontmatter"
        end_frontmatter = content.find("---", 3)
        assert end_frontmatter != -1, f"{skill_name} SKILL.md missing closing frontmatter delimiter"

        frontmatter = content[3:end_frontmatter]
        assert "name:" in frontmatter, f"{skill_name} missing name in frontmatter"
        assert "description:" in frontmatter, f"{skill_name} missing description in frontmatter"

        # 3. Check references directory
        ref_dir = skill_dir / "references"
        assert ref_dir.is_dir(), f"{skill_name} missing references directory"
        assert len(list(ref_dir.iterdir())) > 0, f"{skill_name} references directory empty"

        # 4. Check scripts directory
        scripts_dir = skill_dir / "scripts"
        assert scripts_dir.is_dir(), f"{skill_name} missing scripts directory"
        py_scripts = [f for f in scripts_dir.iterdir() if f.suffix == ".py"]
        assert len(py_scripts) > 0, f"{skill_name} missing executable Python scripts"

        for script in py_scripts:
            src = script.read_text(encoding="utf-8")
            assert "_vendor" in src or "sys.path" in src, f"{script.name} should configure _vendor/sys.path"
