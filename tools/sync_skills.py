#!/usr/bin/env python3
"""
tools/sync_skills.py
====================
Synchronizes packaged mechanics agent skills to the global agent skills directory
(defaults to C:/Users/Administrator/.agents/skills/).

Supports:
- --source: path to staged bundles or dist/skills
- --target: global destination directory
- --dry-run: inspect differences and hashes without applying changes
- --apply: apply synchronization
"""

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

DEFAULT_GLOBAL_TARGET = Path("C:/Users/Administrator/.agents/skills")

EXPECTED_SKILLS: Set[str] = {
    "mechanics-scoping-review",
    "openalex-database",
    "mechanics-evidence-extraction",
    "mechanics-figure",
    "mechanics-paper-polishing",
    "mechanics-paper-reviewer",
}


def _hash_file(p: Path) -> str:
    if not p.is_file():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sync_skills(
    source_dir: Path,
    target_dir: Path,
    dry_run: bool = True,
    allowed_skills: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    summary = {
        "source": str(source_dir.resolve()),
        "target": str(target_dir.resolve()),
        "dry_run": dry_run,
        "skills_synced": [],
        "added_files": [],
        "updated_files": [],
        "unchanged_files": [],
        "backups_created": [],
    }

    # Find skill subdirectories in source
    candidates = [
        d for d in source_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    ]

    # If allowed_skills is explicitly given, filter strictly
    # If not given, filter to EXPECTED_SKILLS if any match is present
    if allowed_skills is not None:
        skill_dirs = [d for d in candidates if d.name in allowed_skills]
    else:
        has_expected = any(d.name in EXPECTED_SKILLS for d in candidates)
        if has_expected:
            skill_dirs = [d for d in candidates if d.name in EXPECTED_SKILLS]
        else:
            skill_dirs = candidates

    print(f"=== Sync Skills: {'DRY RUN' if dry_run else 'APPLYING CHANGES'} ===")
    print(f"  Source: {source_dir}")
    print(f"  Target: {target_dir}")
    print(f"  Discovered skills: {[d.name for d in skill_dirs]}\n")

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = target_dir / ".backups" / timestamp

    for s_dir in sorted(skill_dirs, key=lambda p: p.name):
        skill_name = s_dir.name
        dest_skill_dir = target_dir / skill_name
        summary["skills_synced"].append(skill_name)

        for root, dirs, files in os.walk(s_dir):
            for file in files:
                src_file = Path(root) / file
                rel_path = src_file.relative_to(s_dir)
                dst_file = dest_skill_dir / rel_path

                src_hash = _hash_file(src_file)
                dst_hash = _hash_file(dst_file) if dst_file.is_file() else None

                if dst_hash is None:
                    summary["added_files"].append(f"{skill_name}/{rel_path}")
                    print(f"  [ADD] {skill_name}/{rel_path} ({src_hash[:8]}...)")
                    if not dry_run:
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                elif src_hash != dst_hash:
                    summary["updated_files"].append(f"{skill_name}/{rel_path}")
                    print(f"  [UPDATE] {skill_name}/{rel_path} ({dst_hash[:8]}... -> {src_hash[:8]}...)")
                    if not dry_run:
                        # Create backup of existing file before overwrite
                        backup_file = backup_root / skill_name / rel_path
                        backup_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(dst_file, backup_file)
                        summary["backups_created"].append(str(backup_file))

                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                else:
                    summary["unchanged_files"].append(f"{skill_name}/{rel_path}")

    print(f"\nSummary: {len(summary['skills_synced'])} skills | "
          f"{len(summary['added_files'])} to add | "
          f"{len(summary['updated_files'])} to update | "
          f"{len(summary['unchanged_files'])} unchanged | "
          f"{len(summary['backups_created'])} backed up.")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Synchronize packaged skills to global directory.")
    parser.add_argument("--source", type=str, default="dist/skills", help="Source directory of skill bundles")
    parser.add_argument("--target", type=str, default=str(DEFAULT_GLOBAL_TARGET), help="Target global directory")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run without applying changes")
    parser.add_argument("--apply", action="store_true", default=False, help="Apply synchronization changes")
    args = parser.parse_args()

    is_dry = True
    if args.apply:
        is_dry = False
    elif args.dry_run:
        is_dry = True

    sync_skills(Path(args.source), Path(args.target), dry_run=is_dry)


if __name__ == "__main__":
    main()
