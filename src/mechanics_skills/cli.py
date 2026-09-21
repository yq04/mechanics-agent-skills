"""
Command-line interfaces for mechanics-agent-skills:
- mechanics-search: Multi-source literature retrieval
- mechanics-citations: Forward and backward citation snowballing & main path
- mechanics-oa: Open Access PDF discovery
- mechanics-extract: PDF & text evidence & formula extraction
- mechanics-review: End-to-end PRISMA scoping review generation
"""

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from mechanics_skills.identifiers import generate_dedup_key, normalize_doi, fuzzy_title_match
from mechanics_skills.models import PaperRecord, OAResult
from mechanics_skills.providers.arxiv import ArXivProvider
from mechanics_skills.providers.crossref import CrossrefProvider
from mechanics_skills.providers.openalex import OpenAlexProvider
from mechanics_skills.providers.semantic_scholar import SemanticScholarProvider
from mechanics_skills.providers.unpaywall import UnpaywallProvider
from mechanics_skills.search import search_literature, expand_mechanics_query
from mechanics_skills.screening import screen_papers, PRISMACounter
from mechanics_skills.citations import snowball_citations, extract_main_path, generate_mermaid_citation_network
from mechanics_skills.extraction import extract_evidence_from_pdf, extract_evidence_from_text, EvidenceCard
from mechanics_skills.bibtex import papers_to_bibtex
from mechanics_skills.writing import generate_prisma_mermaid, generate_evidence_matrix_markdown, generate_review_draft_sections


def search_all_sources(
    query: str,
    limit_per_source: int = 15,
    sources: Optional[List[str]] = None,
    client: Optional[Any] = None,
    silent: bool = False,
) -> List[PaperRecord]:
    """Search literature across chosen providers and deduplicate."""
    return search_literature(
        query=query,
        sources=sources,
        limit_per_source=limit_per_source,
        expand=False,
        client=client,
        silent=silent,
    )


def search_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-search."""
    parser = argparse.ArgumentParser(
        prog="mechanics-search",
        description="Multi-source literature search across Crossref, OpenAlex, arXiv, and Semantic Scholar.",
    )
    parser.add_argument("query", type=str, help="Search query string")
    parser.add_argument("--limit", type=int, default=15, help="Max results per database")
    parser.add_argument("--output", type=str, default="", help="Path to save JSON results")
    parser.add_argument("--markdown", type=str, default="", help="Path to save Markdown summary table")
    parser.add_argument(
        "--sources",
        type=str,
        default="crossref,openalex,arxiv",
        help="Comma-separated sources (crossref,openalex,arxiv,semantic_scholar)",
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="Expand query with mechanics taxonomy",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Stdout output format",
    )

    parsed = parser.parse_args(args)
    selected_sources = [s.strip().lower() for s in parsed.sources.split(",") if s.strip()]

    silent = parsed.format == "json"
    results = search_literature(
        query=parsed.query,
        limit_per_source=parsed.limit,
        sources=selected_sources,
        expand=parsed.expand,
        silent=silent,
    )

    if parsed.format == "json":
        json_output = [r.to_dict() for r in results]
        print(json.dumps(json_output, indent=2, ensure_ascii=False))
    elif parsed.format == "markdown":
        print(render_markdown_table(parsed.query, results))
    else:
        print(f"\nTotal deduplicated literature retrieved: {len(results)}\n")
        for i, p in enumerate(results[:10], 1):
            auth = ", ".join(p.authors[:3]) if p.authors else "Unknown"
            source_display = ", ".join(p.sources) if p.sources else "unknown"
            print(f"[{str(i).rjust(2)}] {p.title}")
            print(f"     Authors: {auth}")
            print(f"     Year: {p.year} | Journal: {p.journal} | Citations: {p.citations} | Source: {source_display}")
            print(f"     DOI: {p.doi or 'N/A'}")
            if p.oa_url:
                print(f"     OA URL: {p.oa_url}")
            print()

    if parsed.output:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.output)), exist_ok=True)
        with open(parsed.output, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, ensure_ascii=False, indent=2)
        if parsed.format != "json":
            print(f"Saved JSON results to: {parsed.output}")

    if parsed.markdown:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.markdown)), exist_ok=True)
        with open(parsed.markdown, "w", encoding="utf-8") as f:
            f.write(render_markdown_table(parsed.query, results))
        if parsed.format != "json":
            print(f"Saved Markdown summary to: {parsed.markdown}")

    return 0


def render_markdown_table(query: str, results: List[PaperRecord]) -> str:
    """Render a list of papers as a GitHub-flavored Markdown table."""
    lines = [
        f"# Literature Search Results: {query}\n",
        f"Total retrieved: **{len(results)}** papers.\n",
        "| # | Year | Title | Authors | Journal | Citations | DOI |",
        "|---|------|-------|---------|---------|-----------|-----|",
    ]
    for i, p in enumerate(results, 1):
        authors_str = ", ".join(p.authors[:2]) + (" et al." if len(p.authors) > 2 else "")
        clean_title = p.title.replace("|", "&#124;")
        clean_journal = (p.journal or "").replace("|", "&#124;")
        doi_link = f"[{clean_title}](https://doi.org/{p.doi})" if p.doi else clean_title
        doi_cell = f"`{p.doi}`" if p.doi else "-"
        lines.append(
            f"| {i} | {p.year or '-'} | {doi_link} | {authors_str} | {clean_journal} | {p.citations or 0} | {doi_cell} |"
        )
    return "\n".join(lines) + "\n"


def traverse_citations(
    doi: str,
    limit: int = 20,
    client: Optional[Any] = None,
    silent: bool = False,
) -> Dict[str, Any]:
    """Retrieve forward (cited_by) and backward (references) citations via OpenAlex."""
    clean_d = normalize_doi(doi) or doi.lower().strip()
    result: Dict[str, Any] = {
        "seed_doi": clean_d,
        "seed_title": "",
        "seed_year": None,
        "seed_citations": 0,
        "references": [],
        "cited_by": [],
    }

    openalex = OpenAlexProvider(client=client)
    data = openalex.get_work(clean_d)
    if not data or not data.get("id"):
        if not silent:
            print(f"[Warning] Failed to fetch seed paper via OpenAlex: {doi}", file=sys.stderr)
        return result

    result["seed_title"] = data.get("title") or ""
    result["seed_year"] = data.get("publication_year")
    result["seed_citations"] = data.get("cited_by_count", 0)
    ref_ids = data.get("referenced_works", [])
    openalex_id = data.get("id", "")

    if not silent:
        print(f"Seed paper identified: '{result['seed_title']}' ({result['seed_year']})")
        print(f"Total recorded references: {len(ref_ids)} | Total cited by: {result['seed_citations']}")

    if ref_ids:
        sample_refs = ref_ids[:limit]
        ref_works = openalex.batch_lookup("works", sample_refs, id_field="openalex_id")
        for it in ref_works:
            r_doi = normalize_doi(it.get("doi")) or ""
            r_title = it.get("title") or ""
            r_year = it.get("publication_year")
            r_cites = it.get("cited_by_count", 0)
            r_auth = [
                a.get("author", {}).get("display_name", "")
                for a in it.get("authorships", [])
                if a.get("author", {}).get("display_name")
            ]
            result["references"].append({
                "doi": r_doi,
                "title": r_title,
                "year": r_year,
                "authors": r_auth,
                "citation_count": r_cites,
            })

    if openalex_id and result["seed_citations"] > 0:
        clean_oa_id = openalex_id.split("/")[-1]
        cite_data = openalex.search_works(
            filter_params={"cites": clean_oa_id},
            sort="cited_by_count:desc",
            per_page=min(limit, 100),
        )
        for it in cite_data.get("results", []):
            c_doi = normalize_doi(it.get("doi")) or ""
            c_title = it.get("title") or ""
            c_year = it.get("publication_year")
            c_cites = it.get("cited_by_count", 0)
            c_auth = [
                a.get("author", {}).get("display_name", "")
                for a in it.get("authorships", [])
                if a.get("author", {}).get("display_name")
            ]
            result["cited_by"].append({
                "doi": c_doi,
                "title": c_title,
                "year": c_year,
                "authors": c_auth,
                "citation_count": c_cites,
            })

    return result


def citations_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-citations."""
    parser = argparse.ArgumentParser(
        prog="mechanics-citations",
        description="Traverse citation network backwards and forwards via OpenAlex.",
    )
    parser.add_argument("doi", type=str, help="Seed paper DOI")
    parser.add_argument("--limit", type=int, default=20, help="Max citations/references to retrieve")
    parser.add_argument("--output", type=str, default="", help="Path to save JSON graph")
    parser.add_argument("--mermaid", type=str, default="", help="Path to save Mermaid diagram file (.mmd)")
    parser.add_argument("--format", choices=["text", "json", "mermaid"], default="text", help="Output format")

    parsed = parser.parse_args(args)
    silent = parsed.format in ("json", "mermaid")

    graph_data = snowball_citations([parsed.doi], max_depth=1, max_papers_per_hop=parsed.limit)

    if parsed.format == "json":
        print(json.dumps(graph_data, indent=2, ensure_ascii=False))
    elif parsed.format == "mermaid":
        mmd = generate_mermaid_citation_network(graph_data)
        print(mmd)
    else:
        print(f"\nSeed Paper DOI: {parsed.doi}")
        print(f"Total Nodes: {len(graph_data['nodes'])} | Total Edges: {len(graph_data['edges'])}")
        main_paths = extract_main_path(graph_data)
        if main_paths:
            print("\n--- Identified Main Citation Path ---")
            for p in main_paths[0]:
                print(f" -> {p.get('title')} ({p.get('year')}) [DOI: {p.get('doi')}]")

    if parsed.output:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.output)), exist_ok=True)
        with open(parsed.output, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        if parsed.format == "text":
            print(f"\nSaved citation network to: {parsed.output}")

    if parsed.mermaid:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.mermaid)), exist_ok=True)
        mmd_content = generate_mermaid_citation_network(graph_data)
        with open(parsed.mermaid, "w", encoding="utf-8") as f:
            f.write(mmd_content)
        if parsed.format == "text":
            print(f"Saved Mermaid citation diagram to: {parsed.mermaid}")

    return 0


def find_oa(doi: str, client: Optional[Any] = None) -> OAResult:
    """Find Open Access PDF link using Unpaywall and OpenAlex fallback."""
    clean_d = normalize_doi(doi) or doi.strip()
    unpaywall = UnpaywallProvider(client=client)
    res = unpaywall.find_oa(clean_d)
    if res.is_oa and res.pdf_url:
        return res

    try:
        openalex = OpenAlexProvider(client=client)
        data = openalex.get_work(clean_d)
        oa_info = data.get("open_access") or {}
        if oa_info.get("is_oa"):
            return OAResult(
                doi=clean_d,
                is_oa=True,
                oa_status=oa_info.get("oa_status"),
                pdf_url=oa_info.get("oa_url"),
                host_type=data.get("primary_location", {}).get("source", {}).get("type"),
                title=data.get("title") or res.title,
            )
    except Exception:
        pass

    return res


def oa_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-oa."""
    parser = argparse.ArgumentParser(
        prog="mechanics-oa",
        description="Find free Open Access PDF for a given DOI.",
    )
    parser.add_argument("doi", type=str, help="Paper DOI")
    parser.add_argument("--output", type=str, default="", help="Path to save JSON result")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    parsed = parser.parse_args(args)
    res = find_oa(parsed.doi)

    if parsed.format == "json":
        print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"DOI: {res.doi}")
        print(f"Title: {res.title}")
        print(f"Is Open Access: {res.is_oa} ({res.oa_status})")
        if res.pdf_url:
            print(f"PDF / Full Text Link: {res.pdf_url}")
        else:
            print("No free Open Access PDF found. May require institutional subscription (Elsevier/Springer/ASME).")

    if parsed.output:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.output)), exist_ok=True)
        with open(parsed.output, "w", encoding="utf-8") as f:
            json.dump(res.to_dict(), f, ensure_ascii=False, indent=2)
        if parsed.format != "json":
            print(f"Saved OA result to: {parsed.output}")

    return 0


def extract_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-extract."""
    parser = argparse.ArgumentParser(
        prog="mechanics-extract",
        description="Extract mechanics evidence, constitutive properties, and candidate formulas from PDF or text.",
    )
    parser.add_argument("source", type=str, help="Path to PDF file or text file")
    parser.add_argument("--title", type=str, default="", help="Paper/document title")
    parser.add_argument("--doi", type=str, default="", help="Paper DOI")
    parser.add_argument("--output", type=str, default="", help="Path to save extracted JSON evidence cards")
    parser.add_argument("--markdown", type=str, default="", help="Path to save Markdown evidence matrix table")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format")

    parsed = parser.parse_args(args)
    src_path = Path(parsed.source)

    if not src_path.exists():
        print(f"Error: Source file does not exist: {parsed.source}", file=sys.stderr)
        return 1

    doc_title = parsed.title or src_path.stem
    doi = parsed.doi or None

    if src_path.suffix.lower() == ".pdf":
        cards = extract_evidence_from_pdf(src_path, document_title=doc_title, doi=doi)
    else:
        with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()
        cards = extract_evidence_from_text(
            raw_text,
            document_title=doc_title,
            doi=doi,
            page_number=1,
            source_type="text",
        )

    card_dicts = [c.to_dict() for c in cards]

    if parsed.format == "json":
        print(json.dumps(card_dicts, indent=2, ensure_ascii=False))
    elif parsed.format == "markdown":
        print(generate_evidence_matrix_markdown(card_dicts))
    else:
        print(f"\nExtracted {len(cards)} mechanics evidence cards from '{src_path.name}':\n")
        for i, c in enumerate(cards, 1):
            pg_display = f"Page {c.page_number}" if c.page_number is not None else "Abstract"
            print(f"[{i}] {pg_display} | Type: {c.element_type.upper()} | Confidence: {c.confidence:.2f}")
            print(f"    Excerpt: {c.verbatim_excerpt[:120]}...")
            if c.extracted_parameters:
                print(f"    Parameters: {c.extracted_parameters}")
            print()

    if parsed.output:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.output)), exist_ok=True)
        with open(parsed.output, "w", encoding="utf-8") as f:
            json.dump(card_dicts, f, ensure_ascii=False, indent=2)
        if parsed.format == "text":
            print(f"Saved evidence JSON to: {parsed.output}")

    if parsed.markdown:
        os.makedirs(os.path.dirname(os.path.abspath(parsed.markdown)), exist_ok=True)
        with open(parsed.markdown, "w", encoding="utf-8") as f:
            f.write(generate_evidence_matrix_markdown(card_dicts))
        if parsed.format == "text":
            print(f"Saved Markdown matrix to: {parsed.markdown}")

    return 0


def review_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-review (End-to-end PRISMA Scoping Review)."""
    parser = argparse.ArgumentParser(
        prog="mechanics-review",
        description="End-to-end PRISMA-ScR literature retrieval, 5D screening, and review generation.",
    )
    parser.add_argument("query", type=str, help="Research review topic / query")
    parser.add_argument("--limit", type=int, default=10, help="Max results per database")
    parser.add_argument("--sources", type=str, default="crossref,openalex,arxiv", help="Comma-separated sources")
    parser.add_argument("--expand", action="store_true", help="Expand query with mechanics taxonomy")
    parser.add_argument("--output-dir", type=str, default="review_artifacts", help="Directory to save review outputs")

    parsed = parser.parse_args(args)
    selected_sources = [s.strip().lower() for s in parsed.sources.split(",") if s.strip()]
    out_dir = Path(parsed.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Starting PRISMA-ScR Review Workflow for: {repr(parsed.query)} ===")

    counter = PRISMACounter()
    papers = search_literature(
        query=parsed.query,
        sources=selected_sources,
        limit_per_source=parsed.limit,
        expand=parsed.expand,
        silent=False,
    )
    counter.record_identification(len(papers))
    print(f"\n[Identification] Retrieved {len(papers)} unique candidate records.")

    screening_results = screen_papers(papers, counter=counter)
    included_papers: List[PaperRecord] = []
    for p, sr in zip(papers, screening_results):
        if sr.category in ("Included / Priority", "Contextual / Background"):
            included_papers.append(p)

    print(f"[Screening] Screened {len(papers)} papers using 5D mechanics rubric.")
    print(f"   Priority / Included: {counter.included}")
    print(f"   Assessed for Eligibility: {counter.assessed_eligibility}")
    print(f"   Excluded: {counter.screened_excluded}")

    bib_content = papers_to_bibtex(included_papers)
    bib_path = out_dir / "references.bib"
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(bib_content)
    print(f"[Export] Saved BibTeX for {len(included_papers)} included papers to: {bib_path}")

    flowchart_mmd = generate_prisma_mermaid(counter)
    mmd_path = out_dir / "prisma_flowchart.mmd"
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(flowchart_mmd)
    print(f"[Export] Saved PRISMA flowchart to: {mmd_path}")

    evidence_cards: List[EvidenceCard] = []
    for p in included_papers:
        text = f"{p.title}\n\n{p.abstract}"
        cards = extract_evidence_from_text(text, document_title=p.title, doi=p.doi, page_number=1)
        evidence_cards.extend(cards)

    review_draft = generate_review_draft_sections(included_papers, [c.to_dict() for c in evidence_cards], counter=counter)
    draft_path = out_dir / "review_draft.md"
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(review_draft)
    print(f"[Export] Saved Scoping Review draft to: {draft_path}")

    log_path = out_dir / "screening_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump([sr.to_dict() for sr in screening_results], f, ensure_ascii=False, indent=2)
    print(f"[Export] Saved Screening audit log to: {log_path}")

    print("\n=== PRISMA-ScR Review Completed Successfully! ===")
    return 0


def _get_sample_spec_data(template_name: str) -> Dict[str, Any]:
    """Return a concrete, valid sample FigureSpec for a given template."""
    import numpy as np

    if template_name == "stress_contour":
        x = np.linspace(-5, 5, 35).tolist()
        y = np.linspace(-5, 5, 35).tolist()
        return {
            "template": "stress_contour",
            "title": "Crack-Tip Normal Stress Distribution",
            "layout": "single_column",
            "data": {
                "x": x,
                "y": y,
                "field_name": "sigma_yy",
                "unit": "MPa",
                "colormap": "coolwarm",
                "cracks": [{"segment": [[-4, 0], [0, 0]]}],
            },
            "conventions": {"sign_convention": "tension_positive"},
        }
    elif template_name == "sif_curve":
        theta = np.linspace(0, np.pi / 2, 25).tolist()
        k_cdse = (1.0 + 0.18 * np.cos(2 * np.array(theta))).tolist()
        k_iso = [1.0] * 25
        return {
            "template": "sif_curve",
            "title": "Normalized Mode I SIF along Crack Front",
            "layout": "single_column",
            "data": {
                "curves": [
                    {"label": "Cadmium Selenide (TI)", "x": theta, "y": k_cdse, "color": "#1f77b4"},
                    {"label": "Isotropic Baseline", "x": theta, "y": k_iso, "color": "#ff7f0e", "linestyle": "--"},
                ],
                "baseline_reference": True,
                "xlabel": "Crack Front Angle theta [rad]",
                "ylabel": "Normalized SIF K_I / K_0",
            },
            "conventions": {"sif_normalization": "standard"},
        }
    elif template_name == "interaction_heatmap":
        mat = [
            [1.00, 0.22, 0.08, 0.03],
            [0.22, 1.00, 0.25, 0.07],
            [0.08, 0.25, 1.00, 0.21],
            [0.03, 0.07, 0.21, 1.00],
        ]
        return {
            "template": "interaction_heatmap",
            "title": "Crack Interaction Transmission Matrix",
            "layout": "single_column",
            "data": {
                "matrix": mat,
                "x_labels": ["Crack 1", "Crack 2", "Crack 3", "Crack 4"],
                "y_labels": ["Crack 1", "Crack 2", "Crack 3", "Crack 4"],
                "colorbar_label": "Transmission Coefficient Lambda_ij",
                "colormap": "viridis",
                "annotate": True,
            },
        }
    elif template_name == "asymptotic_comparison":
        x = np.linspace(0.02, 0.85, 30).tolist()
        exact = (1.0 / (1.0 - np.array(x)**2)).tolist()
        asymp_1 = (1.0 + np.array(x)**2).tolist()
        asymp_2 = (1.0 + np.array(x)**2 + np.array(x)**4).tolist()
        return {
            "template": "asymptotic_comparison",
            "title": "Asymptotic Expansion vs Global Exact Solution",
            "layout": "single_column",
            "data": {
                "x": x,
                "exact": exact,
                "exact_label": "Exact Solution",
                "asymptotic": {
                    "Order O(eps^2)": asymp_1,
                    "Order O(eps^4)": asymp_2,
                },
                "xlabel": "Small Parameter epsilon = a/h",
                "ylabel": "Normalized SIF K_I / K_0",
            },
        }
    elif template_name == "crack_geometry":
        return {
            "template": "crack_geometry",
            "title": "Interacting Parallel Penny-Shaped Cracks",
            "layout": "single_column",
            "data": {
                "cracks": [
                    {"center": [0.0, 1.8], "radius": 1.5, "label": "Crack A (a_1 = 1.5)"},
                    {"center": [0.0, -1.8], "radius": 1.5, "label": "Crack B (a_2 = 1.5)"},
                ],
                "loading": {"type": "tension", "label": "sigma_0 (Far-field tension)"},
                "dimensions": [
                    {"start": [0.0, -1.8], "end": [0.0, 1.8], "label": "h = 3.6", "label_offset": [0.5, 0.0]}
                ],
                "bounds": [-6, 6, -5, 5],
            },
        }
    return {}


def figure_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-figure."""
    from mechanics_skills.figure import (
        FigureSpec,
        validate_figure_spec,
        render_figure,
        ALLOWED_TEMPLATES,
    )

    parser = argparse.ArgumentParser(
        prog="mechanics-figure",
        description="Publication-ready mechanics figure generation and verification (85mm single-column, 175mm double-column, 300+ DPI vector).",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    render_p = subparsers.add_parser("render", help="Render figure from JSON FigureSpec")
    render_p.add_argument("spec", type=str, help="Path to FigureSpec JSON file")
    render_p.add_argument("--output-dir", type=str, default="figure_artifacts", help="Output directory")

    val_p = subparsers.add_parser("validate", help="Validate FigureSpec against mechanics standards")
    val_p.add_argument("spec", type=str, help="Path to FigureSpec JSON file")

    tpl_p = subparsers.add_parser("template", help="Generate sample FigureSpec JSON for a template")
    tpl_p.add_argument("name", choices=sorted(list(ALLOWED_TEMPLATES)), help="Template name")
    tpl_p.add_argument("--output", type=str, default="", help="Path to save template JSON")

    passed_args = list(args if args is not None else sys.argv[1:])
    if passed_args and passed_args[0] not in ("render", "validate", "template", "-h", "--help"):
        if passed_args[0].endswith(".json") or Path(passed_args[0]).is_file():
            passed_args.insert(0, "render")

    parsed = parser.parse_args(passed_args)

    if parsed.subcommand == "render":
        spec_file = Path(parsed.spec)
        if not spec_file.is_file():
            print(f"Error: Specification file not found: {parsed.spec}", file=sys.stderr)
            return 1

        with open(spec_file, "r", encoding="utf-8") as f:
            spec_data = json.load(f)

        findings = validate_figure_spec(spec_data)
        has_critical = False
        if findings:
            print(f"Auditing FigureSpec for {spec_file.name}:")
            for fnd in findings:
                print(f"  [{fnd.severity.upper()}] ({fnd.category}) {fnd.message}")
                if fnd.severity == "critical":
                    has_critical = True

        if has_critical:
            print("Error: Spec contains critical integrity violations; aborting render.", file=sys.stderr)
            return 1

        manifest = render_figure(spec_data, parsed.output_dir)
        print(chr(10) + f"Rendered '{manifest['template']}' ({manifest['layout']}) to: {parsed.output_dir}")
        print(f"  Dimensions: {manifest['dimensions']['width_mm']:.1f} x {manifest['dimensions']['height_mm']:.1f} mm ({manifest['dimensions']['dpi']} DPI)")
        print("  Exported artifacts:")
        for fmt, path in manifest["export_files"].items():
            print(f"    - {fmt}: {path}")
        print(f"  Data SHA-256: {manifest['data_hashes']['raw_data_sha256'][:16]}...")
        return 0

    elif parsed.subcommand == "validate":
        spec_file = Path(parsed.spec)
        if not spec_file.is_file():
            print(f"Error: Specification file not found: {parsed.spec}", file=sys.stderr)
            return 1

        with open(spec_file, "r", encoding="utf-8") as f:
            spec_data = json.load(f)

        findings = validate_figure_spec(spec_data)
        if not findings:
            print(f"Validation successful: '{spec_file.name}' satisfies all publication and mechanics integrity criteria.")
            return 0
        else:
            print(f"Validation findings for '{spec_file.name}':")
            has_critical = False
            for fnd in findings:
                print(f"  [{fnd.severity.upper()}] ({fnd.category}) {fnd.message}")
                if fnd.severity == "critical":
                    has_critical = True
            return 1 if has_critical else 0

    elif parsed.subcommand == "template":
        sample_data = _get_sample_spec_data(parsed.name)
        sample_json = json.dumps(sample_data, indent=2, ensure_ascii=False)
        if parsed.output:
            out_p = Path(parsed.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(sample_json, encoding="utf-8")
            print(f"Saved sample template for '{parsed.name}' to: {parsed.output}")
        else:
            print(sample_json)
        return 0

    else:
        parser.print_help()
        return 1






# -------------------------------------------------------------------------
# Mechanics Paper Polishing CLI
# -------------------------------------------------------------------------

def polish_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-polish."""
    from mechanics_skills.polishing import (
        analyze_manuscript,
        prepare_polish_request,
        validate_edits,
        apply_edits,
    )
    from mechanics_skills.integrity import ConventionRegistry

    parser = argparse.ArgumentParser(
        prog="mechanics-polish",
        description="Mechanics Paper Polishing & Notation Guard CLI.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze manuscript for math protection, cliches, and notation warnings")
    p_analyze.add_argument("manuscript", type=str, help="Path to Markdown or LaTeX manuscript")
    p_analyze.add_argument("--conventions", type=str, default="", help="Path to conventions JSON file")
    p_analyze.add_argument("--output", type=str, default="", help="Path to save JSON analysis")
    p_analyze.add_argument("--format", choices=["text", "json"], default="text", help="Stdout output format")

    # prepare
    p_prepare = subparsers.add_parser("prepare", help="Prepare a constrained polish task package for host LLM")
    p_prepare.add_argument("manuscript", type=str, help="Path to manuscript")
    p_prepare.add_argument("--conventions", type=str, default="", help="Path to conventions JSON file")
    p_prepare.add_argument("--output-dir", type=str, default="", help="Directory to save polish request artifacts")
    p_prepare.add_argument("--output", type=str, default="", help="Path to save request JSON")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate edit proposals against manuscript and protection zones")
    p_val.add_argument("manuscript", type=str, help="Path to original manuscript")
    p_val.add_argument("proposals", type=str, help="Path to proposals.json")

    # apply
    p_apply = subparsers.add_parser("apply", help="Apply validated edit proposals safely to generate polished text")
    p_apply.add_argument("manuscript", type=str, help="Path to original manuscript")
    p_apply.add_argument("proposals", type=str, help="Path to proposals.json")
    p_apply.add_argument("--output", type=str, default="", help="Path to write polished manuscript (defaults to polished_<name>)")
    p_apply.add_argument("--diff", type=str, default="", help="Path to save diff records JSON")

    parsed = parser.parse_args(args)

    if parsed.subcommand == "analyze":
        p = Path(parsed.manuscript)
        if not p.is_file():
            print(f"Error: Manuscript file not found: {parsed.manuscript}", file=sys.stderr)
            return 1
        text = p.read_text(encoding="utf-8")

        conv = None
        if parsed.conventions and Path(parsed.conventions).is_file():
            conv = json.loads(Path(parsed.conventions).read_text(encoding="utf-8"))

        analysis = analyze_manuscript(text, conventions=conv)

        if parsed.format == "json":
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
        else:
            stats = analysis["statistics"]
            print(f"\nManuscript Analysis: '{p.name}'")
            print(f"  Total characters: {stats['char_count']} | Words: {stats['word_count']} | Sections: {stats['section_count']}")
            print(f"  Protected Zones: {stats['protected_zones_count']} (Math: {stats['math_zones_count']})")
            print(f"  Detected Cliches: {stats['cliches_count']}")
            print(f"  Notation Warnings: {stats['notation_warnings_count']}")

            if analysis["cliches"]:
                print("\n  Sample Cliches Detected:")
                for c in analysis["cliches"][:5]:
                    print(f"    - '{c['matched_text']}' -> suggest: {c['replacement_suggestion']}")

            if analysis["notation_warnings"]:
                print("\n  Notation / Mechanics Warnings:")
                for w in analysis["notation_warnings"]:
                    print(f"    - [{w['category']}] {w['message']}")

        if parsed.output:
            out_p = Path(parsed.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
            if parsed.format != "json":
                print(f"\nSaved analysis JSON to: {parsed.output}")
        return 0

    elif parsed.subcommand == "prepare":
        p = Path(parsed.manuscript)
        if not p.is_file():
            print(f"Error: Manuscript file not found: {parsed.manuscript}", file=sys.stderr)
            return 1
        text = p.read_text(encoding="utf-8")

        conv = None
        if parsed.conventions and Path(parsed.conventions).is_file():
            conv = json.loads(Path(parsed.conventions).read_text(encoding="utf-8"))

        analysis = analyze_manuscript(text, conventions=conv)
        req = prepare_polish_request(analysis)

        req_json = json.dumps(req, indent=2, ensure_ascii=False)
        if parsed.output_dir:
            out_dir = Path(parsed.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "polish_request.json").write_text(req_json, encoding="utf-8")
            (out_dir / "analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Prepared polish task package in: {out_dir}")
            print(f"Status: {req['status']} (Ready for host model proposals generation)")
        elif parsed.output:
            out_p = Path(parsed.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(req_json, encoding="utf-8")
            print(f"Saved polish request package to: {parsed.output}")
        else:
            print(req_json)
        return 0

    elif parsed.subcommand == "validate":
        p_ms = Path(parsed.manuscript)
        p_prop = Path(parsed.proposals)
        if not p_ms.is_file() or not p_prop.is_file():
            print("Error: Input files not found", file=sys.stderr)
            return 1
        text = p_ms.read_text(encoding="utf-8")
        proposals_data = json.loads(p_prop.read_text(encoding="utf-8"))
        proposals = proposals_data.get("proposals", proposals_data) if isinstance(proposals_data, dict) else proposals_data

        findings = validate_edits(text, proposals)
        if not findings:
            print("Validation successful: all edit proposals adhere to math and terminology protection constraints.")
            return 0
        else:
            print(f"Validation findings ({len(findings)}):")
            has_crit = False
            for f in findings:
                print(f"  [{f.severity.upper()}] ({f.category}) {f.message}")
                if f.severity == "critical":
                    has_crit = True
            return 1 if has_crit else 0

    elif parsed.subcommand == "apply":
        p_ms = Path(parsed.manuscript)
        p_prop = Path(parsed.proposals)
        if not p_ms.is_file() or not p_prop.is_file():
            print("Error: Input files not found", file=sys.stderr)
            return 1
        text = p_ms.read_text(encoding="utf-8")
        proposals_data = json.loads(p_prop.read_text(encoding="utf-8"))
        proposals = proposals_data.get("proposals", proposals_data) if isinstance(proposals_data, dict) else proposals_data

        try:
            modified_text, diffs = apply_edits(text, proposals)
        except ValueError as e:
            print(f"Error applying edits: {e}", file=sys.stderr)
            return 1

        out_path = Path(parsed.output) if parsed.output else p_ms.parent / f"polished_{p_ms.name}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(modified_text, encoding="utf-8")
        print(f"Successfully applied {len(diffs)} edit(s).")
        print(f"Polished manuscript written to: {out_path}")

        if parsed.diff:
            diff_p = Path(parsed.diff)
            diff_p.parent.mkdir(parents=True, exist_ok=True)
            diff_p.write_text(json.dumps(diffs, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Diff records saved to: {parsed.diff}")
        return 0

    else:
        parser.print_help()
        return 1


# -------------------------------------------------------------------------
# Mechanics Peer Review CLI
# -------------------------------------------------------------------------

def peer_review_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-peer-review."""
    from mechanics_skills.reviewer import (
        audit_scientific_soundness,
        generate_review_report_markdown,
        compare_revision,
        prepare_review_package,
        JOURNAL_PROFILES,
    )

    parser = argparse.ArgumentParser(
        prog="mechanics-peer-review",
        description="Simulated Mechanics Peer Review & Five-Dimensional Soundness Audit CLI.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit manuscript against the 5-dimensional soundness criteria")
    p_audit.add_argument("manuscript", type=str, help="Path to manuscript")
    p_audit.add_argument("--journal", type=str, default="jmps", choices=list(JOURNAL_PROFILES.keys()), help="Target journal profile")
    p_audit.add_argument("--output", type=str, default="", help="Path to save JSON audit results")
    p_audit.add_argument("--markdown", type=str, default="", help="Path to save Markdown peer review report")

    # prepare
    p_prep = subparsers.add_parser("prepare", help="Prepare a comprehensive review task package for reviewer models")
    p_prep.add_argument("manuscript", type=str, help="Path to manuscript")
    p_prep.add_argument("--journal", type=str, default="jmps", choices=list(JOURNAL_PROFILES.keys()), help="Target journal profile")
    p_prep.add_argument("--output-dir", type=str, default="", help="Directory to save review package artifacts")

    # compare
    p_comp = subparsers.add_parser("compare", help="Compare revised manuscript against previous review findings")
    p_comp.add_argument("previous_review", type=str, help="Path to previous review JSON")
    p_comp.add_argument("revised_manuscript", type=str, help="Path to revised manuscript")
    p_comp.add_argument("--output", type=str, default="", help="Path to save comparison JSON")

    # report
    p_rep = subparsers.add_parser("report", help="Render Markdown report from an existing review JSON")
    p_rep.add_argument("review_json", type=str, help="Path to review JSON file")
    p_rep.add_argument("--output", type=str, default="", help="Path to save Markdown report")

    parsed = parser.parse_args(args)

    if parsed.subcommand == "audit":
        p = Path(parsed.manuscript)
        if not p.is_file():
            print(f"Error: Manuscript file not found: {parsed.manuscript}", file=sys.stderr)
            return 1
        text = p.read_text(encoding="utf-8")

        audit_res = audit_scientific_soundness(text, journal=parsed.journal)
        md_report = generate_review_report_markdown(audit_res)

        print(f"\nSimulated Peer Review Audit: '{p.name}' -> Target: {audit_res['journal_profile']['full_name']}")
        print(f"  Overall Soundness: {audit_res['overall_soundness'].upper()}")
        print(f"  Major Concerns: {audit_res['major_concerns_count']} | Minor Concerns: {audit_res['minor_concerns_count']}")

        for dim_key, dim_info in audit_res["dimensions"].items():
            st = dim_info["status"].upper()
            print(f"  - {dim_info['name']}: {st} ({len(dim_info['findings'])} findings)")

        if parsed.output:
            out_p = Path(parsed.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(json.dumps(audit_res, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Saved review JSON to: {parsed.output}")

        if parsed.markdown:
            md_p = Path(parsed.markdown)
            md_p.parent.mkdir(parents=True, exist_ok=True)
            md_p.write_text(md_report, encoding="utf-8")
            print(f"Saved Markdown report to: {parsed.markdown}")

        return 0

    elif parsed.subcommand == "prepare":
        p = Path(parsed.manuscript)
        if not p.is_file():
            print(f"Error: Manuscript file not found: {parsed.manuscript}", file=sys.stderr)
            return 1
        text = p.read_text(encoding="utf-8")

        pkg = prepare_review_package(text, journal=parsed.journal)
        md_report = generate_review_report_markdown(pkg["soundness_audit"])

        if parsed.output_dir:
            out_dir = Path(parsed.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
            (out_dir / "review_draft.md").write_text(md_report, encoding="utf-8")
            print(f"Prepared review package in: {out_dir}")
        else:
            print(json.dumps(pkg, indent=2, ensure_ascii=False))
        return 0

    elif parsed.subcommand == "compare":
        p_rev = Path(parsed.previous_review)
        p_ms = Path(parsed.revised_manuscript)
        if not p_rev.is_file() or not p_ms.is_file():
            print("Error: Input files not found", file=sys.stderr)
            return 1

        prev_data = json.loads(p_rev.read_text(encoding="utf-8"))
        rev_text = p_ms.read_text(encoding="utf-8")

        comp = compare_revision(prev_data, rev_text)
        print(f"\n{comp['summary']}")
        print(f"  Resolved: {comp['resolved_count']} | Persisting: {comp['persisting_count']} | New: {comp['new_findings_count']}")

        if parsed.output:
            out_p = Path(parsed.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(json.dumps(comp, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Saved comparison to: {parsed.output}")
        return 0

    elif parsed.subcommand == "report":
        p_rev = Path(parsed.review_json)
        if not p_rev.is_file():
            print(f"Error: Review file not found: {parsed.review_json}", file=sys.stderr)
            return 1
        review_data = json.loads(p_rev.read_text(encoding="utf-8"))
        if "soundness_audit" in review_data:
            review_data = review_data["soundness_audit"]

        md_report = generate_review_report_markdown(review_data)
        if parsed.output:
            out_p = Path(parsed.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(md_report, encoding="utf-8")
            print(f"Saved Markdown report to: {parsed.output}")
        else:
            print(md_report)
        return 0

    else:
        parser.print_help()
        return 1




# -------------------------------------------------------------------------
# Scientific Integrity Pipeline CLI
# -------------------------------------------------------------------------

def integrity_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-integrity."""
    from mechanics_skills.integrity import run_integrity_pipeline

    parser = argparse.ArgumentParser(
        prog="mechanics-integrity",
        description="7-Gate Scientific Integrity Pipeline & Publication Readiness CLI.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    p_check = subparsers.add_parser("check", help="Run 7-gate scientific integrity check on manuscript or workflow run config")
    p_check.add_argument("target", type=str, help="Path to manuscript file (.md, .tex) or workflow run.json / manifest.json")
    p_check.add_argument("--stage", type=str, default="final", help="Workflow stage filter (e.g. pre-review, final)")
    p_check.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_check.add_argument("--output", type=str, default="", help="Path to save JSON integrity report")

    parsed = parser.parse_args(args)
    if not parsed.subcommand or parsed.subcommand != "check":
        parser.print_help()
        return 1

    target_path = Path(parsed.target)
    if not target_path.exists():
        print(f"Error: Target file not found: {parsed.target}", file=sys.stderr)
        return 1

    manuscript_text = ""
    data_refs = []
    conventions = None
    options = {}

    if target_path.suffix.lower() == ".json":
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "manuscript_path" in data and os.path.isfile(data["manuscript_path"]):
                manuscript_text = Path(data["manuscript_path"]).read_text(encoding="utf-8")
            elif "manuscript" in data and isinstance(data["manuscript"], str):
                manuscript_text = data["manuscript"]
            elif "stages" in data:
                out_dir = Path(data.get("output_dir", target_path.parent))
                ms_candidates = [
                    out_dir / "manuscript" / "polished_manuscript.md",
                    out_dir / "manuscript" / "original_manuscript.md",
                    out_dir / "evidence" / "review_draft.md",
                ]
                for c in ms_candidates:
                    if c.is_file():
                        manuscript_text = c.read_text(encoding="utf-8")
                        break

            if "conventions_path" in data and os.path.isfile(data["conventions_path"]):
                conventions = json.loads(Path(data["conventions_path"]).read_text(encoding="utf-8"))
            elif "conventions" in data:
                conventions = data["conventions"]

            if "data_refs" in data:
                data_refs = list(data["data_refs"])

            if "options" in data:
                options = dict(data["options"])

        except Exception as e:
            print(f"Error loading JSON target: {e}", file=sys.stderr)
            return 1
    else:
        manuscript_text = target_path.read_text(encoding="utf-8", errors="ignore")

    if not manuscript_text:
        manuscript_text = target_path.read_text(encoding="utf-8", errors="ignore")

    report = run_integrity_pipeline(
        manuscript_text,
        data_refs=data_refs,
        conventions=conventions,
        options=options,
    )

    if parsed.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"\nScientific Integrity Pipeline Audit: '{target_path.name}'")
        print(f"  Overall Status: {report['status'].upper()}")
        print(f"  Readiness Gate: {report['readiness']}")
        print(f"  Summary: {report['summary']}\n")
        print("  Gate-by-Gate Evaluation:")
        for g_id, g_info in report["gates"].items():
            print(f"    [{g_id}] {g_info['name']}: {g_info['status'].upper()} ({len(g_info['findings'])} findings)")
            for fnd in g_info["findings"][:3]:
                print(f"         - [{fnd['severity'].upper()}] {fnd['message']}")

    if parsed.output:
        out_p = Path(parsed.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if parsed.format != "json":
            print(f"\nSaved integrity report JSON to: {parsed.output}")

    if report["readiness"] == "ready_for_author_review" or report["status"] == "pass":
        return 0
    elif report["readiness"] == "needs_evidence" or report["status"] == "needs_evidence":
        return 2
    else:
        return 4


# -------------------------------------------------------------------------
# Mechanics Workflow CLI
# -------------------------------------------------------------------------

def workflow_cli(args: Optional[List[str]] = None) -> int:
    """CLI entry point for mechanics-workflow."""
    from mechanics_skills.workflow import run_workflow, resume_workflow, STAGES

    parser = argparse.ArgumentParser(
        prog="mechanics-workflow",
        description="End-to-End Resumable Mechanics Research Workflow Engine CLI.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # run
    p_run = subparsers.add_parser("run", help="Run full mechanics research lifecycle from config")
    p_run.add_argument("config", type=str, help="Path to workflow run configuration JSON file")
    p_run.add_argument("--output-dir", type=str, default="artifacts/workflow-run", help="Directory to save workflow artifacts")
    p_run.add_argument("--offline", action="store_true", help="Run in offline deterministic mode using local fixtures")
    p_run.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    # resume
    p_resume = subparsers.add_parser("resume", help="Resume an existing workflow run from manifest")
    p_resume.add_argument("manifest", type=str, help="Path to workflow.manifest.json, manifest.json, or output directory")
    p_resume.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    # status
    p_status = subparsers.add_parser("status", help="Inspect status of an existing workflow manifest")
    p_status.add_argument("manifest", type=str, help="Path to manifest or output directory")
    p_status.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    parsed = parser.parse_args(args)

    if parsed.subcommand == "run":
        cfg_path = Path(parsed.config)
        if not cfg_path.is_file():
            print(f"Error: Configuration file not found: {parsed.config}", file=sys.stderr)
            return 1

        try:
            manifest = run_workflow(
                config_path=str(cfg_path),
                output_dir=parsed.output_dir,
                offline=parsed.offline,
            )
        except Exception as e:
            print(f"Workflow execution failed: {e}", file=sys.stderr)
            return 1

        if parsed.format == "json":
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        else:
            print(f"\nMechanics Research Workflow Run: {manifest['run_id']}")
            print(f"  Overall Status: {manifest['status'].upper()}")
            print(f"  Output Directory: {manifest['output_dir']}")
            print(f"  Handoff Memo: {manifest.get('handoff', {}).get('memo_path', 'N/A')}\n")
            print("  Stages Execution:")
            for s_name in STAGES:
                s_info = manifest["stages"].get(s_name, {})
                st = s_info.get("status", "unknown").upper()
                n_art = len(s_info.get("artifacts", []))
                n_warn = len(s_info.get("warnings", []))
                print(f"    - {s_name}: {st} ({n_art} artifacts, {n_warn} warnings)")

        st = manifest["status"]
        if st == "completed":
            return 0
        elif st == "needs_input":
            return 2
        elif st in ("blocked", "failed"):
            return 4
        elif st == "partial":
            return 3
        return 0

    elif parsed.subcommand == "resume":
        target = Path(parsed.manifest)
        if not target.exists():
            print(f"Error: Manifest target not found: {parsed.manifest}", file=sys.stderr)
            return 1

        try:
            manifest = resume_workflow(manifest_path=str(target))
        except Exception as e:
            print(f"Workflow resume failed: {e}", file=sys.stderr)
            return 1

        if parsed.format == "json":
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        else:
            print(f"\nMechanics Research Workflow Resumed: {manifest['run_id']}")
            print(f"  Overall Status: {manifest['status'].upper()}")
            print(f"  Output Directory: {manifest['output_dir']}")
            print(f"  Handoff Memo: {manifest.get('handoff', {}).get('memo_path', 'N/A')}\n")
            print("  Stages Status:")
            for s_name in STAGES:
                s_info = manifest["stages"].get(s_name, {})
                st = s_info.get("status", "unknown").upper()
                n_art = len(s_info.get("artifacts", []))
                n_warn = len(s_info.get("warnings", []))
                print(f"    - {s_name}: {st} ({n_art} artifacts, {n_warn} warnings)")

        st = manifest["status"]
        if st == "completed":
            return 0
        elif st == "needs_input":
            return 2
        elif st in ("blocked", "failed"):
            return 4
        elif st == "partial":
            return 3
        return 0

    elif parsed.subcommand == "status":
        target = Path(parsed.manifest)
        if target.is_dir():
            m_path = target / "workflow.manifest.json"
            if not m_path.is_file():
                m_path = target / "manifest.json"
        else:
            m_path = target

        if not m_path.is_file():
            print(f"Error: Manifest file not found in: {parsed.manifest}", file=sys.stderr)
            return 1

        manifest = json.loads(m_path.read_text(encoding="utf-8"))
        if parsed.format == "json":
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
        else:
            print(f"\nWorkflow Run Status: {manifest['run_id']}")
            print(f"  Overall Status: {manifest['status'].upper()}")
            print(f"  Created: {manifest.get('created_at')} | Updated: {manifest.get('updated_at')}")
            print("  Stages:")
            for s_name, s_info in manifest.get("stages", {}).items():
                print(f"    - {s_name}: {s_info.get('status', 'unknown').upper()} (Artifacts: {len(s_info.get('artifacts', []))})")
        return 0

    else:
        parser.print_help()
        return 1


def main() -> int:
    """Unified entry point for mechanics-skills command."""
    parser = argparse.ArgumentParser(
        prog="mechanics-skills",
        description="Mechanics Research Agent Skills Suite (v3.1.0)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    subparsers.add_parser("search", help="Search literature")
    subparsers.add_parser("citations", help="Traverse citations")
    subparsers.add_parser("oa", help="Find open access PDF")
    subparsers.add_parser("extract", help="Extract mechanics evidence from PDF/text")
    subparsers.add_parser("review", help="End-to-end PRISMA scoping review")
    subparsers.add_parser("figure", help="Generate publication-ready mechanics figures")
    subparsers.add_parser("polish", help="Paper polishing & notation guard")
    subparsers.add_parser("peer-review", help="Simulated mechanics peer review & 5D soundness audit")
    subparsers.add_parser("integrity", help="7-Gate Scientific Integrity Pipeline audit")
    subparsers.add_parser("workflow", help="End-to-end resumable mechanics research workflow")

    if len(sys.argv) < 2:
        parser.print_help()
        return 1

    cmd = sys.argv[1]
    remaining = sys.argv[2:]

    if cmd == "search":
        return search_cli(remaining)
    elif cmd == "citations":
        return citations_cli(remaining)
    elif cmd == "oa":
        return oa_cli(remaining)
    elif cmd == "extract":
        return extract_cli(remaining)
    elif cmd == "review":
        return review_cli(remaining)
    elif cmd == "figure":
        return figure_cli(remaining)
    elif cmd == "polish":
        return polish_cli(remaining)
    elif cmd == "peer-review":
        return peer_review_cli(remaining)
    elif cmd == "integrity":
        return integrity_cli(remaining)
    elif cmd == "workflow":
        return workflow_cli(remaining)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
