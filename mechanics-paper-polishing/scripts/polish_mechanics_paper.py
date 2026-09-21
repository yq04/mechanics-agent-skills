#!/usr/bin/env python3
"""
polish_mechanics_paper.py
=========================
CLI wrapper for mechanics paper polishing and notation guard.
"""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
_vendor_dir = Path(__file__).resolve().parent / "_vendor"
if _vendor_dir.is_dir() and str(_vendor_dir) not in sys.path:
    sys.path.insert(0, str(_vendor_dir))
_src_dir = _repo_root / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from mechanics_skills.cli import polish_cli


def main():
    sys.exit(polish_cli())


if __name__ == "__main__":
    main()
