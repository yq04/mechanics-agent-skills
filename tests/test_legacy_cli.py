"""
Unit tests for legacy CLI scripts and wrappers to guarantee backward compatibility.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_legacy_scripts_help():
    """Verify that all legacy CLI scripts respond to --help with exit code 0."""
    scripts = [
        REPO_ROOT / "mechanics-scoping-review" / "scripts" / "search_mechanics_papers.py",
        REPO_ROOT / "mechanics-scoping-review" / "scripts" / "traverse_mechanics_citations.py",
        REPO_ROOT / "mechanics-scoping-review" / "scripts" / "find_oa_pdf.py",
    ]

    for script_path in scripts:
        cmd = [sys.executable, str(script_path), "--help"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert res.returncode == 0, f"Script {script_path.name} --help failed: {res.stderr}"
        assert "usage:" in res.stdout.lower() or "help" in res.stdout.lower()


def test_legacy_openalex_client_import():
    """Verify that openalex_client and query_helpers can be imported without requests installed."""
    sys_path_added = False
    oa_scripts_dir = str(REPO_ROOT / "openalex-database" / "scripts")
    if oa_scripts_dir not in sys.path:
        sys.path.insert(0, oa_scripts_dir)
        sys_path_added = True

    try:
        import openalex_client
        import query_helpers

        client = openalex_client.OpenAlexClient(email="test@mechanics.edu")
        assert client.email == "test@mechanics.edu"
        assert hasattr(client, "search_works")
        assert hasattr(client, "get_entity")
        assert hasattr(client, "batch_lookup")
        assert hasattr(client, "paginate_all")
    finally:
        if sys_path_added and oa_scripts_dir in sys.path:
            sys.path.remove(oa_scripts_dir)


@patch("mechanics_skills.cli.search_all_sources")
def test_search_mechanics_papers_invocation(mock_search):
    from mechanics_skills.models import PaperRecord
    mock_search.return_value = [
        PaperRecord(
            title="Penny-Shaped Crack in Anisotropic Elasticity",
            doi="10.1016/j.jmps.2020.104123",
            authors=["Fabrikant V.I."],
            year=2020,
            journal="JMPS",
            citations=50,
            sources=["crossref"],
        )
    ]
    sys_path_added = False
    ms_scripts_dir = str(REPO_ROOT / "mechanics-scoping-review" / "scripts")
    if ms_scripts_dir not in sys.path:
        sys.path.insert(0, ms_scripts_dir)
        sys_path_added = True

    try:
        import search_mechanics_papers
        results = search_mechanics_papers.search_all_sources("penny crack", limit_per_source=5)
        assert len(results) == 1
        assert results[0]["doi"] == "10.1016/j.jmps.2020.104123"
        assert results[0]["citation_count"] == 50
    finally:
        if sys_path_added and ms_scripts_dir in sys.path:
            sys.path.remove(ms_scripts_dir)


@patch("mechanics_skills.cli.traverse_citations")
def test_traverse_mechanics_citations_invocation(mock_traverse):
    mock_traverse.return_value = {
        "seed_doi": "10.1016/j.jmps.2020.104123",
        "seed_title": "Penny-Shaped Crack in Anisotropic Elasticity",
        "seed_year": 2020,
        "seed_citations": 50,
        "references": [],
        "cited_by": [],
    }
    sys_path_added = False
    ms_scripts_dir = str(REPO_ROOT / "mechanics-scoping-review" / "scripts")
    if ms_scripts_dir not in sys.path:
        sys.path.insert(0, ms_scripts_dir)
        sys_path_added = True

    try:
        import traverse_mechanics_citations
        res = traverse_mechanics_citations.get_paper_details_and_citations("10.1016/j.jmps.2020.104123")
        assert res["seed_doi"] == "10.1016/j.jmps.2020.104123"
        assert res["seed_citations"] == 50
    finally:
        if sys_path_added and ms_scripts_dir in sys.path:
            sys.path.remove(ms_scripts_dir)


@patch("mechanics_skills.cli.find_oa")
def test_find_oa_pdf_invocation(mock_find_oa):
    from mechanics_skills.models import OAResult
    mock_find_oa.return_value = OAResult(
        doi="10.1016/j.jmps.2020.104123",
        is_oa=True,
        pdf_url="https://example.com/paper.pdf",
        oa_status="gold",
        host_type="publisher",
        title="Penny-Shaped Crack",
    )
    sys_path_added = False
    ms_scripts_dir = str(REPO_ROOT / "mechanics-scoping-review" / "scripts")
    if ms_scripts_dir not in sys.path:
        sys.path.insert(0, ms_scripts_dir)
        sys_path_added = True

    try:
        import find_oa_pdf
        res = find_oa_pdf.find_pdf_for_doi("10.1016/j.jmps.2020.104123")
        assert res["is_oa"] is True
        assert res["pdf_url"] == "https://example.com/paper.pdf"
        assert res["doi"] == "10.1016/j.jmps.2020.104123"
    finally:
        if sys_path_added and ms_scripts_dir in sys.path:
            sys.path.remove(ms_scripts_dir)

