#!/usr/bin/env python3
"""
render_mechanics_figure.py
==========================
CLI wrapper for generating publication-ready solid and fracture mechanics figures.
Supports 85mm single-column and 175mm double-column layouts, vector PDF/SVG,
300+ DPI PNG, and automated data integrity provenance hashing.
"""

import sys
from pathlib import Path

# Ensure src/ is on sys.path
_repo_root = Path(__file__).resolve().parent.parent.parent
_vendor_dir = Path(__file__).resolve().parent / "_vendor"
if _vendor_dir.is_dir() and str(_vendor_dir) not in sys.path:
    sys.path.insert(0, str(_vendor_dir))
_src_dir = _repo_root / "src"
if _src_dir.is_dir() and str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from mechanics_skills.cli import figure_cli


def main():
    sys.exit(figure_cli())


if __name__ == "__main__":
    main()
