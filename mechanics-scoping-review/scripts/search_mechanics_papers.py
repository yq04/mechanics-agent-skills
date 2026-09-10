#!/usr/bin/env python3
"""
search_mechanics_papers.py
==========================
Multi-source literature search CLI for Solid Mechanics, Fracture Mechanics, and Elasticity.
Sources: Crossref, OpenAlex, arXiv, and Semantic Scholar.
Anchor: DOI (Digital Object Identifier).
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.parse
import re

USER_AGENT = "Mozilla/5.0 (compatible; MechanicsScopingReviewBot/2.0; +mailto:academic_researcher@mechanics.edu)"

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()

def search_crossref(query, limit=15):
    papers = []
    try:
        url = "https://api.crossref.org/works?query=" + urllib.parse.quote(query) + "&rows=" + str(limit) + "&mailto=academic_researcher@mechanics.edu"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("message", {}).get("items", [])
            for it in items:
                doi = it.get("DOI", "").lower().strip()
                title = clean_text((it.get("title") or [""])[0])
                authors = []
                for a in it.get("author", []):
                    name = (a.get("given", "") + " " + a.get("family", "")).strip()
                    if name:
                        authors.append(name)
                year = None
                if "published-print" in it and "date-parts" in it["published-print"]:
                    year = it["published-print"]["date-parts"][0][0]
                elif "published-online" in it and "date-parts" in it["published-online"]:
                    year = it["published-online"]["date-parts"][0][0]
                elif "issued" in it and "date-parts" in it["issued"]:
                    year = it["issued"]["date-parts"][0][0]
                journal = clean_text((it.get("container-title") or [""])[0])
                citations = it.get("is-referenced-by-count", 0)
                abstract = clean_text(it.get("abstract", ""))
                abstract = re.sub(r"<[^>]+>", "", abstract)
                if doi and title:
                    papers.append({
                        "doi": doi,
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "journal": journal,
                        "citation_count": citations,
                        "abstract": abstract,
                        "oa_url": "",
                        "source": "crossref"
                    })
    except Exception as e:
        print("[Notice] Crossref search error: " + str(e), file=sys.stderr)
    return papers

def search_openalex(query, limit=15):
    papers = []
    try:
        url = "https://api.openalex.org/works?search=" + urllib.parse.quote(query) + "&per_page=" + str(limit) + "&mailto=academic_researcher@mechanics.edu"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            for it in results:
                raw_doi = it.get("doi") or ""
                doi = raw_doi.replace("https://doi.org/", "").lower().strip()
                title = clean_text(it.get("title") or "")
                authors = [clean_text(a.get("author", {}).get("display_name", "")) for a in it.get("authorships", [])]
                year = it.get("publication_year")
                host = it.get("primary_location", {}) or {}
                source_info = host.get("source", {}) or {}
                journal = clean_text(source_info.get("display_name", ""))
                citations = it.get("cited_by_count", 0)
                oa_url = (it.get("open_access", {}) or {}).get("oa_url", "")
                abstract = ""
                inv = it.get("abstract_inverted_index")
                if inv:
                    word_pos = []
                    for word, positions in inv.items():
                        for pos in positions:
                            word_pos.append((pos, word))
                    word_pos.sort(key=lambda x: x[0])
                    abstract = clean_text(" ".join([w[1] for w in word_pos]))
                if (doi or raw_doi) and title:
                    papers.append({
                        "doi": doi or raw_doi,
                        "openalex_id": it.get("id", ""),
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "journal": journal,
                        "citation_count": citations,
                        "abstract": abstract,
                        "oa_url": oa_url,
                        "source": "openalex"
                    })
    except Exception as e:
        print("[Notice] OpenAlex search error: " + str(e), file=sys.stderr)
    return papers

def search_arxiv(query, limit=10):
    papers = []
    try:
        url = "http://export.arxiv.org/api/query?search_query=all:" + urllib.parse.quote(query) + "&start=0&max_results=" + str(limit)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.read().decode("utf-8"))
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title = clean_text(entry.find("atom:title", ns).text)
                summary = clean_text(entry.find("atom:summary", ns).text)
                authors = [clean_text(a.find("atom:name", ns).text) for a in entry.findall("atom:author", ns)]
                id_url = entry.find("atom:id", ns).text
                published = entry.find("atom:published", ns).text
                year = int(published[:4]) if published else None
                doi_elem = entry.find("{http://arxiv.org/schemas/atom}doi")
                doi = doi_elem.text.lower().strip() if doi_elem is not None else id_url
                papers.append({
                    "doi": doi,
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "journal": "arXiv preprint",
                    "citation_count": 0,
                    "abstract": summary,
                    "oa_url": id_url,
                    "source": "arxiv"
                })
    except Exception as e:
        print("[Notice] arXiv search error: " + str(e), file=sys.stderr)
    return papers

def search_all_sources(query, limit_per_source=10, sources=None):
    if sources is None:
        sources = ["crossref", "openalex", "arxiv"]
    all_papers = []
    seen_dois = set()
    seen_titles = set()
    print("=== Searching mechanics literature for: " + repr(query) + " ===")
    if "crossref" in sources:
        cr_res = search_crossref(query, limit=limit_per_source)
        print(" [Crossref] Found " + str(len(cr_res)) + " records.")
        for p in cr_res:
            doi = p.get("doi")
            t = p.get("title", "").lower()
            if doi and doi not in seen_dois and t not in seen_titles:
                seen_dois.add(doi)
                seen_titles.add(t)
                all_papers.append(p)
    if "openalex" in sources:
        oa_res = search_openalex(query, limit=limit_per_source)
        print(" [OpenAlex] Found " + str(len(oa_res)) + " records.")
        for p in oa_res:
            doi = p.get("doi")
            t = p.get("title", "").lower()
            if (doi and doi not in seen_dois) or (t and t not in seen_titles):
                if doi: seen_dois.add(doi)
                if t: seen_titles.add(t)
                all_papers.append(p)
    if "arxiv" in sources:
        ar_res = search_arxiv(query, limit=limit_per_source)
        print(" [arXiv] Found " + str(len(ar_res)) + " records.")
        for p in ar_res:
            doi = p.get("doi")
            t = p.get("title", "").lower()
            if (doi and doi not in seen_dois) or (t and t not in seen_titles):
                if doi: seen_dois.add(doi)
                if t: seen_titles.add(t)
                all_papers.append(p)
    all_papers.sort(key=lambda x: x.get("citation_count") or 0, reverse=True)
    return all_papers

def main():
    parser = argparse.ArgumentParser(description="Search mechanics literature across OpenAlex, Crossref, and arXiv.")
    parser.add_argument("query", type=str, help="Search query string")
    parser.add_argument("--limit", type=int, default=15, help="Max results per database")
    parser.add_argument("--output", type=str, default="", help="Path to save JSON results")
    parser.add_argument("--markdown", type=str, default="", help="Path to save Markdown summary table")
    parser.add_argument("--sources", type=str, default="crossref,openalex,arxiv", help="Comma-separated sources")
    args = parser.parse_args()
    selected_sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    results = search_all_sources(args.query, limit_per_source=args.limit, sources=selected_sources)
    print("\nTotal deduplicated literature retrieved: " + str(len(results)) + "\n")
    for i, p in enumerate(results[:10], 1):
        auth = ", ".join(p["authors"][:3]) if p["authors"] else "Unknown"
        print("[" + str(i).rjust(2) + "] " + p["title"])
        print("     Authors: " + auth)
        print("     Year: " + str(p.get("year")) + " | Journal: " + str(p.get("journal")) + " | Citations: " + str(p.get("citation_count")) + " | Source: " + str(p.get("source")))
        print("     DOI: " + str(p["doi"]))
        if p.get("oa_url"):
            print("     OA URL: " + str(p["oa_url"]))
        print()
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("Saved JSON results to: " + args.output)
    if args.markdown:
        os.makedirs(os.path.dirname(os.path.abspath(args.markdown)), exist_ok=True)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write("# Literature Search Results: " + args.query + "\n\n")
            f.write("Total retrieved: **" + str(len(results)) + "** papers.\n\n")
            f.write("| # | Year | Title | Authors | Journal | Citations | DOI |\n")
            f.write("|---|------|-------|---------|---------|-----------|-----\n")
            for i, p in enumerate(results, 1):
                authors_str = ", ".join(p["authors"][:2]) + (" et al." if len(p["authors"]) > 2 else "")
                clean_title = p["title"].replace("|", "&#124;")
                clean_journal = p["journal"].replace("|", "&#124;")
                f.write("| " + str(i) + " | " + str(p.get("year") or "-") + " | [" + clean_title + "](https://doi.org/" + p["doi"] + ") | " + authors_str + " | " + clean_journal + " | " + str(p.get("citation_count", 0)) + " | `" + p["doi"] + "` |\n")
        print("Saved Markdown summary to: " + args.markdown)

if __name__ == "__main__":
    main()