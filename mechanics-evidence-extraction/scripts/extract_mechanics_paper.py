#!/usr/bin/env python3
"""
extract_mechanics_paper.py
==========================
CLI wrapper for extracting mechanics evidence, constitutive tensors,
potential representations, formula candidates, and benchmark tables from PDF/text.
Refactored for mechanics-agent-skills v3.0.0.
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

from mechanics_skills.cli import extract_cli
from mechanics_skills.extraction import (
    extract_evidence_from_pdf,
    extract_evidence_from_text,
    EvidenceCard,
)


def extract_evidence(source_path, title="", doi=None):
    """Legacy helper returning evidence cards as dictionaries."""
    p = Path(source_path)
    if p.suffix.lower() == ".pdf":
        cards = extract_evidence_from_pdf(p, document_title=title or p.stem, doi=doi)
    else:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            cards = extract_evidence_from_text(f.read(), document_title=title or p.stem, doi=doi)
    return [c.to_dict() for c in cards]


def main():
    sys.exit(extract_cli())


if __name__ == "__main__":
    main()
