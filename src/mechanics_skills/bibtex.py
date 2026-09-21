"""
BibTeX generation and parsing utilities for academic mechanics papers.
"""

from collections import defaultdict
import re
from typing import Any, Dict, List, Optional

from mechanics_skills.models import PaperRecord


def generate_citekey(paper: PaperRecord, seen_keys: Optional[Dict[str, int]] = None) -> str:
    """
    Generate clean academic citekey in AuthorYear format (e.g. Collins1963, Fabrikant1989).
    Resolves collisions by appending a, b, c... suffixes.
    """
    first_author = "Anon"
    if paper.authors:
        raw_author = paper.authors[0].strip()
        if "," in raw_author:
            surname = raw_author.split(",")[0].strip()
        else:
            parts = raw_author.split()
            if len(parts) >= 2 and len(parts[-1]) <= 3 and parts[-1].isupper():
                surname = parts[0]
            else:
                surname = parts[-1] if parts else "Anon"
        clean_surname = re.sub(r"[^a-zA-Z]", "", surname)
        if clean_surname:
            first_author = clean_surname.capitalize()

    year_str = str(paper.year) if paper.year else "NoYear"
    base_key = f"{first_author}{year_str}"

    if seen_keys is None:
        return base_key

    if base_key not in seen_keys:
        seen_keys[base_key] = 1
        return base_key
    else:
        idx = seen_keys[base_key]
        seen_keys[base_key] += 1
        suffix = chr(ord("a") + idx - 1)
        return f"{base_key}{suffix}"


def paper_to_bibtex(paper: PaperRecord, citekey: Optional[str] = None) -> str:
    """Format a single PaperRecord as a standard BibTeX entry."""
    key = citekey or generate_citekey(paper)
    entry_type = "article"
    if not paper.journal and (paper.arxiv_id or (paper.doi and "arxiv" in paper.doi.lower())):
        entry_type = "misc"

    fields: List[str] = []
    # Title
    clean_title = paper.title.replace("{", "").replace("}", "").strip()
    fields.append(f"  title = {{{clean_title}}}")

    # Authors formatted with 'and'
    if paper.authors:
        clean_authors = " and ".join([a.replace("{", "").replace("}", "").strip() for a in paper.authors])
        fields.append(f"  author = {{{clean_authors}}}")

    if paper.journal:
        fields.append(f"  journal = {{{paper.journal.strip()}}}")

    if paper.year:
        fields.append(f"  year = {{{paper.year}}}")

    if paper.doi:
        fields.append(f"  doi = {{{paper.doi.strip()}}}")

    if paper.url:
        fields.append(f"  url = {{{paper.url.strip()}}}")
    elif paper.doi:
        fields.append(f"  url = {{https://doi.org/{paper.doi.strip()}}}")

    if paper.arxiv_id:
        fields.append(f"  eprint = {{{paper.arxiv_id.strip()}}}")
        fields.append("  archivePrefix = {arXiv}")

    body = ",\n".join(fields)
    return f"@{entry_type}{{{key},\n{body}\n}}"


def papers_to_bibtex(papers: List[PaperRecord]) -> str:
    """Format a list of PaperRecords as a complete BibTeX file."""
    seen_keys: Dict[str, int] = {}
    entries: List[str] = []
    for p in papers:
        key = generate_citekey(p, seen_keys=seen_keys)
        entries.append(paper_to_bibtex(p, citekey=key))
    return "\n\n".join(entries) + "\n"


def parse_bibtex_entry(bib_str: str) -> List[Dict[str, Any]]:
    """
    Lightweight, robust BibTeX parser using stdlib regex.
    Extracts entry_type, citekey, and key-value fields.
    """
    entries: List[Dict[str, Any]] = []
    entry_pattern = re.compile(r"@([a-zA-Z]+)\s*\{\s*([^,\s]+)\s*,\s*(.*?)\n\s*\}", re.DOTALL)
    field_pattern = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*[\{"](.*?)(?<!\\)[\}"]', re.DOTALL)

    for match in entry_pattern.finditer(bib_str):
        etype = match.group(1).lower()
        key = match.group(2).strip()
        body = match.group(3)

        fields: Dict[str, str] = {
            "ENTRYTYPE": etype,
            "ID": key,
        }

        for fmatch in field_pattern.finditer(body):
            fname = fmatch.group(1).lower().strip()
            fval = fmatch.group(2).strip()
            # Clean internal spacing
            fval = re.sub(r"\s+", " ", fval)
            fields[fname] = fval

        entries.append(fields)

    return entries
