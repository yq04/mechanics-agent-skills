#!/usr/bin/env python3
"""
find_oa_pdf.py
==============
Look up free Open Access full text / PDF for a given DOI using Unpaywall and OpenAlex.
"""

import sys
import os
import argparse
import json
import urllib.request
import urllib.parse

USER_AGENT = "Mozilla/5.0 (compatible; MechanicsOABot/2.0; +mailto:academic_researcher@mechanics.edu)"

def find_pdf_for_doi(doi):
    clean_doi = doi.replace("https://doi.org/", "").lower().strip()
    res = {
        "doi": clean_doi,
        "is_oa": False,
        "pdf_url": None,
        "oa_status": None,
        "host_type": None,
        "title": ""
    }

    try:
        url = "https://api.unpaywall.org/v2/" + clean_doi + "?email=academic_researcher@mechanics.edu"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            res["is_oa"] = data.get("is_oa", False)
            res["oa_status"] = data.get("oa_status")
            res["title"] = data.get("title") or ""
            best = data.get("best_oa_location") or {}
            res["pdf_url"] = best.get("url_for_pdf") or best.get("url")
            res["host_type"] = best.get("host_type")
            if res["pdf_url"]:
                return res
    except Exception as e:
        print("[Notice] Unpaywall lookup failed: " + str(e), file=sys.stderr)

    try:
        url = "https://api.openalex.org/works/https://doi.org/" + clean_doi + "?mailto=academic_researcher@mechanics.edu"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            oa_info = data.get("open_access") or {}
            if oa_info.get("is_oa"):
                res["is_oa"] = True
                res["oa_status"] = oa_info.get("oa_status")
                res["pdf_url"] = oa_info.get("oa_url")
                res["title"] = data.get("title") or ""
    except Exception as e:
        print("[Notice] OpenAlex OA fallback failed: " + str(e), file=sys.stderr)

    return res

def main():
    parser = argparse.ArgumentParser(description="Find open access PDF for given DOI.")
    parser.add_argument("doi", type=str, help="Paper DOI")
    args = parser.parse_args()
    res = find_pdf_for_doi(args.doi)
    print("DOI: " + res["doi"])
    print("Title: " + res.get("title", ""))
    print("Is Open Access: " + str(res["is_oa"]) + " (" + str(res["oa_status"]) + ")")
    if res["pdf_url"]:
        print("PDF / Full Text Link: " + res["pdf_url"])
    else:
        print("No free Open Access PDF found. May require institutional subscription (Elsevier/Springer/ASME).")

if __name__ == "__main__":
    main()