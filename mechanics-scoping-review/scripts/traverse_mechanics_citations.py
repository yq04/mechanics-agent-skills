#!/usr/bin/env python3
"""
traverse_mechanics_citations.py
===============================
Smart backward (references) and forward (citations) snowballing via OpenAlex.
Anchor: DOI.
Refactored for mechanics-agent-skills v3.0.0 (delegating to mechanics_skills core).
"""

import os
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

from mechanics_skills.cli import citations_cli, traverse_citations


def get_paper_details_and_citations(doi, limit=30):
    """Legacy compatibility function for citation traversal."""
    return traverse_citations(doi, limit=limit)


def main():
    sys.exit(citations_cli())


if __name__ == "__main__":
    main()

