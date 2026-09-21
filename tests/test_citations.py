"""
Unit tests for citation snowballing, SPC main-path analysis, and Mermaid visualization.
"""

import pytest

from mechanics_skills.citations import (
    compute_spc_weights,
    extract_main_path,
    generate_mermaid_citation_network,
    snowball_citations,
)


def test_compute_spc_weights_diamond():
    """
    Test Search Path Count (SPC) on a canonical diamond graph:
         A (source, 1963)
        / \
       B   C (intermediates, 1987, 1989)
        \ /
         D (sink, 2021)
    Knowledge flow: A -> B -> D and A -> C -> D.
    Path counts:
      N_sources: A:1, B:1, C:1, D:2
      N_sinks: A:2, B:1, C:1, D:1
    Edge SPC = N_sources(u) * N_sinks(v):
      (A, B): 1 * 1 = 1
      (A, C): 1 * 1 = 1
      (B, D): 1 * 1 = 1
      (C, D): 1 * 1 = 1
    """
    nodes = {
        "A": {"doi": "A", "title": "Paper A", "year": 1963, "citations": 100},
        "B": {"doi": "B", "title": "Paper B", "year": 1987, "citations": 80},
        "C": {"doi": "C", "title": "Paper C", "year": 1989, "citations": 90},
        "D": {"doi": "D", "title": "Paper D", "year": 2021, "citations": 10},
    }
    # In citation edges, B cites A (citing=B, cited=A), so knowledge flow is A -> B
    edges = [
        {"citing": "B", "cited": "A"},
        {"citing": "C", "cited": "A"},
        {"citing": "D", "cited": "B"},
        {"citing": "D", "cited": "C"},
    ]

    spc = compute_spc_weights(nodes, edges)
    assert spc[("A", "B")] == 1
    assert spc[("A", "C")] == 1
    assert spc[("B", "D")] == 1
    assert spc[("C", "D")] == 1


def test_compute_spc_weights_linear_chain():
    """
    Test SPC on a linear chain: A -> B -> C -> D.
    Paths through every edge are 1.
    """
    nodes = {
        "A": {"doi": "A", "title": "Seminal", "year": 1960, "citations": 200},
        "B": {"doi": "B", "title": "Mid1", "year": 1980, "citations": 100},
        "C": {"doi": "C", "title": "Mid2", "year": 2000, "citations": 50},
        "D": {"doi": "D", "title": "Latest", "year": 2022, "citations": 5},
    }
    edges = [
        {"citing": "B", "cited": "A"},
        {"citing": "C", "cited": "B"},
        {"citing": "D", "cited": "C"},
    ]

    spc = compute_spc_weights(nodes, edges)
    assert spc[("A", "B")] == 1
    assert spc[("B", "C")] == 1
    assert spc[("C", "D")] == 1


def test_extract_main_path():
    """Extracting main path should return the sequence of papers along highest SPC backbone."""
    nodes = {
        "10.1001/a": {"doi": "10.1001/a", "title": "Collins 1963", "year": 1963, "citations": 500},
        "10.1001/b": {"doi": "10.1001/b", "title": "Kachanov 1987", "year": 1987, "citations": 1200},
        "10.1001/c": {"doi": "10.1001/c", "title": "Recent Extension 2021", "year": 2021, "citations": 40},
    }
    edges = [
        {"citing": "10.1001/b", "cited": "10.1001/a"},
        {"citing": "10.1001/c", "cited": "10.1001/b"},
    ]
    graph = {"nodes": nodes, "edges": edges, "seed_dois": ["10.1001/a"]}

    paths = extract_main_path(graph)
    assert len(paths) >= 1
    main_titles = [n["title"] for n in paths[0]]
    assert main_titles == ["Collins 1963", "Kachanov 1987", "Recent Extension 2021"]


def test_generate_mermaid_citation_network():
    """Verify Mermaid diagram generation syntax and classes."""
    nodes = {
        "10.1001/p1": {"doi": "10.1001/p1", "title": "Early Elasticity", "year": 1985, "authors": ["Muskhelishvili NI"], "citations": 300},
        "10.1001/p2": {"doi": "10.1001/p2", "title": "TI Fabrikant Methods", "year": 1995, "authors": ["Fabrikant VI"], "citations": 400},
        "10.1001/p3": {"doi": "10.1001/p3", "title": "Modern Penny Cracks", "year": 2020, "authors": ["Zhang H"], "citations": 50},
    }
    edges = [
        {"citing": "10.1001/p2", "cited": "10.1001/p1"},
        {"citing": "10.1001/p3", "cited": "10.1001/p2"},
    ]
    graph = {"nodes": nodes, "edges": edges, "seed_dois": ["10.1001/p2"]}

    mmd = generate_mermaid_citation_network(graph, highlight_main_path=True)
    assert "flowchart TD" in mmd
    assert "classDef mainPath" in mmd
    assert "classDef seedNode" in mmd
    assert "Fabrikant (1995)" in mmd
    assert "main path" in mmd


def test_snowball_citations_mocked(monkeypatch):
    """Test snowball_citations BFS traversal with a mocked OpenAlex provider."""
    mock_work_seed = {
        "id": "https://openalex.org/W111",
        "doi": "https://doi.org/10.1001/seed",
        "title": "Seed Paper",
        "publication_year": 2010,
        "cited_by_count": 25,
        "referenced_works": ["https://openalex.org/W222"],
        "authorships": [{"author": {"display_name": "Author A"}}]
    }
    mock_work_ref = {
        "id": "https://openalex.org/W222",
        "doi": "https://doi.org/10.1001/ref",
        "title": "Foundational Reference",
        "publication_year": 1990,
        "cited_by_count": 150,
        "referenced_works": [],
        "authorships": [{"author": {"display_name": "Author B"}}]
    }

    class FakeOpenAlex:
        def __init__(self, client=None): pass
        def get_work(self, doi):
            if "seed" in doi:
                return mock_work_seed
            elif "ref" in doi or "W222" in doi:
                return mock_work_ref
            return None
        def batch_lookup(self, entity_type, ids, id_field="openalex_id"):
            return [mock_work_ref]
        def search_works(self, filter_params=None, sort=None, per_page=50):
            return {"results": []}

    monkeypatch.setattr("mechanics_skills.citations.OpenAlexProvider", FakeOpenAlex)

    graph = snowball_citations(["10.1001/seed"], max_depth=1, direction="backward")
    assert "10.1001/seed" in graph["nodes"]
    assert "10.1001/ref" in graph["nodes"]
    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert edge["citing"] == "10.1001/seed"
    assert edge["cited"] == "10.1001/ref"
