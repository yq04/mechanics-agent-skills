#!/usr/bin/env python3
"""
traverse_mechanics_citations.py
===============================
Smart backward (references) and forward (citations) snowballing via OpenAlex & Crossref.
Anchor: DOI.
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.parse
import re

USER_AGENT = "Mozilla/5.0 (compatible; MechanicsCitationBot/2.0; +mailto:academic_researcher@mechanics.edu)"

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()

def get_paper_details_and_citations(doi, limit=30):
    doi_clean = doi.replace("https://doi.org/", "").lower().strip()
    result = {
        "seed_doi": doi_clean,
        "seed_title": "",
        "seed_year": None,
        "seed_citations": 0,
        "references": [],
        "cited_by": []
    }
    
    try:
        url = "https://api.openalex.org/works/https://doi.org/" + doi_clean + "?mailto=academic_researcher@mechanics.edu"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result["seed_title"] = clean_text(data.get("title") or "")
            result["seed_year"] = data.get("publication_year")
            result["seed_citations"] = data.get("cited_by_count", 0)
            ref_ids = data.get("referenced_works", [])
            openalex_id = data.get("id", "")
    except Exception as e:
        print("[Warning] Failed to fetch seed paper via OpenAlex: " + str(e), file=sys.stderr)
        return result

    print("Seed paper identified: '" + result["seed_title"] + "' (" + str(result["seed_year"]) + ")")
    print("Total recorded references: " + str(len(ref_ids)) + " | Total cited by: " + str(result["seed_citations"]))

    if ref_ids:
        sample_refs = ref_ids[:limit]
        filter_str = "|".join([r.split("/")[-1] for r in sample_refs])
        try:
            ref_url = "https://api.openalex.org/works?filter=openalex:" + filter_str + "&per_page=" + str(limit) + "&mailto=academic_researcher@mechanics.edu"
            req = urllib.request.Request(ref_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                ref_data = json.loads(resp.read().decode("utf-8"))
                for it in ref_data.get("results", []):
                    r_doi = (it.get("doi") or "").replace("https://doi.org/", "").lower().strip()
                    r_title = clean_text(it.get("title") or "")
                    r_year = it.get("publication_year")
                    r_cites = it.get("cited_by_count", 0)
                    r_auth = [clean_text(a.get("author", {}).get("display_name", "")) for a in it.get("authorships", [])]
                    result["references"].append({
                        "doi": r_doi,
                        "title": r_title,
                        "year": r_year,
                        "authors": r_auth,
                        "citation_count": r_cites
                    })
        except Exception as e:
            print("[Warning] Failed fetching reference metadata: " + str(e), file=sys.stderr)

    if openalex_id and result["seed_citations"] > 0:
        clean_oa_id = openalex_id.split("/")[-1]
        try:
            cite_url = "https://api.openalex.org/works?filter=cites:" + clean_oa_id + "&sort=cited_by_count:desc&per_page=" + str(limit) + "&mailto=academic_researcher@mechanics.edu"
            req = urllib.request.Request(cite_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                cite_data = json.loads(resp.read().decode("utf-8"))
                for it in cite_data.get("results", []):
                    c_doi = (it.get("doi") or "").replace("https://doi.org/", "").lower().strip()
                    c_title = clean_text(it.get("title") or "")
                    c_year = it.get("publication_year")
                    c_cites = it.get("cited_by_count", 0)
                    c_auth = [clean_text(a.get("author", {}).get("display_name", "")) for a in it.get("authorships", [])]
                    result["cited_by"].append({
                        "doi": c_doi,
                        "title": c_title,
                        "year": c_year,
                        "authors": c_auth,
                        "citation_count": c_cites
                    })
        except Exception as e:
            print("[Warning] Failed fetching citation metadata: " + str(e), file=sys.stderr)

    return result

def main():
    parser = argparse.ArgumentParser(description="Traverse citation network backwards and forwards via OpenAlex.")
    parser.add_argument("doi", type=str, help="Seed paper DOI")
    parser.add_argument("--limit", type=int, default=20, help="Max citations/references to retrieve")
    parser.add_argument("--output", type=str, default="", help="Path to save JSON graph")
    args = parser.parse_args()

    data = get_paper_details_and_citations(args.doi, limit=args.limit)
    print("\n--- Backward Traversal (Key References: " + str(len(data["references"])) + ") ---")
    for i, r in enumerate(data["references"][:8], 1):
        print("[" + str(i).rjust(2) + "] " + r["title"] + " (" + str(r["year"]) + ") - Cited " + str(r["citation_count"]) + " times | DOI: " + str(r["doi"]))

    print("\n--- Forward Traversal (Key Citing Works: " + str(len(data["cited_by"])) + ") ---")
    for i, c in enumerate(data["cited_by"][:8], 1):
        print("[" + str(i).rjust(2) + "] " + c["title"] + " (" + str(c["year"]) + ") - Cited " + str(c["citation_count"]) + " times | DOI: " + str(c["doi"]))

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\nSaved citation network to: " + args.output)

if __name__ == "__main__":
    main()