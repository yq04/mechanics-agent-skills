#!/usr/bin/env python3
"""
tools/build_skill_bundles.py
============================
Builds self-contained distribution bundles for each agent skill in mechanics-agent-skills.
Vendors the core mechanics_skills package into scripts/_vendor/mechanics_skills so that
each skill can be copied to any remote or local agent environment without pre-installing pip packages.

Supports:
- --out: Output directory for bundles (default dist/skills)
- --sync-global: Copy and sync built bundles directly into global skills directory
- --target: Custom global target path (default C:/Users/Administrator/.agents/skills)
"""

import argparse
import os
from pathlib import Path
import shutil
import sys
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SRC_CORE = REPO_ROOT / "src" / "mechanics_skills"
LICENSE_FILE = REPO_ROOT / "LICENSE"
DEFAULT_GLOBAL_TARGET = Path("C:/Users/Administrator/.agents/skills")

EXPECTED_SKILLS = [
    "mechanics-scoping-review",
    "openalex-database",
    "mechanics-evidence-extraction",
    "mechanics-figure",
    "mechanics-paper-polishing",
    "mechanics-paper-reviewer",
]


def find_skills(repo_root: Path):
    skills = []
    for item in repo_root.iterdir():
        if item.is_dir() and (item / "SKILL.md").is_file():
            skills.append(item)
    return sorted(skills, key=lambda p: p.name)


def build_bundle(skill_dir: Path, out_dir: Path):
    skill_name = skill_dir.name
    target_dir = out_dir / skill_name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy SKILL.md
    shutil.copy2(skill_dir / "SKILL.md", target_dir / "SKILL.md")

    # Copy references/ if present
    ref_dir = skill_dir / "references"
    if ref_dir.is_dir():
        shutil.copytree(ref_dir, target_dir / "references")

    # Copy scripts/ if present
    scripts_dir = skill_dir / "scripts"
    target_scripts = target_dir / "scripts"
    if scripts_dir.is_dir():
        shutil.copytree(
            scripts_dir,
            target_scripts,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_vendor"),
        )
    else:
        target_scripts.mkdir(parents=True, exist_ok=True)

    # Vendor core mechanics_skills package
    vendor_target = target_scripts / "_vendor" / "mechanics_skills"
    if vendor_target.exists():
        shutil.rmtree(vendor_target)
    shutil.copytree(
        SRC_CORE,
        vendor_target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    # Copy LICENSE
    if LICENSE_FILE.exists():
        shutil.copy2(LICENSE_FILE, target_dir / "LICENSE")

    # Create zip bundle
    zip_path = out_dir / f"{skill_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(out_dir)
                zf.write(file_path, arcname)

    print(f" Built bundle: {target_dir} -> {zip_path}")


def main():
    parser = argparse.ArgumentParser(description="Build self-contained skill distribution bundles.")
    parser.add_argument("--out", type=str, default="dist/skills", help="Output directory for bundles")
    parser.add_argument("--sync-global", action="store_true", help="Sync bundled skills to global directory")
    parser.add_argument("--target", type=str, default=str(DEFAULT_GLOBAL_TARGET), help="Target global directory")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path

    out_path.mkdir(parents=True, exist_ok=True)
    skills = find_skills(REPO_ROOT)
    skill_names = [s.name for s in skills]
    print(f"Discovered {len(skills)} skills in repository: {skill_names}")

    # Check that all expected skills are present
    missing = [s for s in EXPECTED_SKILLS if s not in skill_names]
    if missing:
        print(f"Warning: Missing expected skills: {missing}", file=sys.stderr)

    for skill in skills:
        build_bundle(skill, out_path)

    print(f"All {len(skills)} skill bundles built successfully in: {out_path}")

    if args.sync_global:
        from tools.sync_skills import sync_skills
        target_dir = Path(args.target)
        print(f"\nSynchronizing all {len(skills)} bundled skills to global target: {target_dir}")
        sync_skills(source_dir=out_path, target_dir=target_dir, dry_run=False)
        print("Global synchronization completed successfully.")


if __name__ == "__main__":
    main()
