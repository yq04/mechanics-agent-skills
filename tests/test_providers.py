"""
Unit tests for academic metadata providers using mock responses.
Strictly offline: tests provider parsing, header construction, and error handling.
"""

from unittest.mock import MagicMock

from mechanics_skills.http import HTTPClient, HTTPResponse
from mechanics_skills.providers.arxiv import ArXivProvider
from mechanics_skills.providers.crossref import CrossrefProvider
from mechanics_skills.providers.openalex import OpenAlexProvider, decode_abstract_inverted_index
from mechanics_skills.providers.semantic_scholar import SemanticScholarProvider
from mechanics_skills.providers.unpaywall import UnpaywallProvider


def test_crossref_provider_parsing():
    mock_payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.1016/j.jmps.2020.104123",
                    "title": ["Exact Solutions for Penny-Shaped Cracks"],
                    "author": [
                        {"given": "V. I.", "family": "Fabrikant"},
                        {"given": "M.", "family": "Kachanov"},
                    ],
                    "published-print": {"date-parts": [[2020, 5, 1]]},
                    "container-title": ["Journal of the Mechanics and Physics of Solids"],
                    "is-referenced-by-count": 45,
                    "abstract": "<jats:p>An exact analytical formulation for crack interaction.</jats:p>",
                    "URL": "https://doi.org/10.1016/j.jmps.2020.104123",
                }
            ]
        }
    }
    mock_client = MagicMock(spec=HTTPClient)
    mock_client.get.return_value = HTTPResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b"",
    )
    mock_client.get.return_value._json = mock_payload

    prov = CrossrefProvider(client=mock_client, email="test@mechanics.edu")
    records = prov.search("crack interaction", limit=5)

    assert len(records) == 1
    rec = records[0]
    assert rec.title == "Exact Solutions for Penny-Shaped Cracks"
    assert rec.doi == "10.1016/j.jmps.2020.104123"
    assert rec.authors == ["V. I. Fabrikant", "M. Kachanov"]
    assert rec.year == 2020
    assert rec.journal == "Journal of the Mechanics and Physics of Solids"
    assert rec.citations == 45
    assert "<jats:p>" not in rec.abstract
    assert "An exact analytical formulation" in rec.abstract
    assert "crossref" in rec.sources

    # Check that client.get was called with mailto in params
    args, kwargs = mock_client.get.call_args
    assert kwargs["params"]["mailto"] == "test@mechanics.edu"


def test_openalex_abstract_decoding():
    inverted_index = {
        "Exact": [0],
        "elastic": [1],
        "fields": [2],
        "around": [3],
        "penny-shaped": [4],
        "cracks.": [5],
    }
    decoded = decode_abstract_inverted_index(inverted_index)
    assert decoded == "Exact elastic fields around penny-shaped cracks."


def test_openalex_provider_parsing_and_page_cap():
    mock_payload = {
        "results": [
            {
                "id": "https://openalex.org/W123456789",
                "doi": "https://doi.org/10.1016/j.jmps.2021.104500",
                "title": "Three-Dimensional Elasticity in Transversely Isotropic Media",
                "publication_year": 2021,
                "authorships": [
                    {"author": {"display_name": "A. E. Green"}},
                    {"author": {"display_name": "I. N. Sneddon"}},
                ],
                "primary_location": {
                    "source": {"display_name": "International Journal of Solids and Structures"}
                },
                "cited_by_count": 88,
                "open_access": {"is_oa": True, "oa_url": "https://example.com/green_sneddon.pdf"},
                "abstract_inverted_index": {"Dual": [0], "integral": [1], "equations.": [2]},
            }
        ]
    }
    mock_client = MagicMock(spec=HTTPClient)
    mock_client.get.return_value = HTTPResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b"",
    )
    mock_client.get.return_value._json = mock_payload

    prov = OpenAlexProvider(client=mock_client, email="test@mechanics.edu")
    # Request 200 per page (exceeding 100)
    records = prov.search("elasticity", limit=200)

    assert len(records) == 1
    rec = records[0]
    assert rec.doi == "10.1016/j.jmps.2021.104500"
    assert rec.citations == 88
    assert rec.abstract == "Dual integral equations."
    assert rec.oa_url == "https://example.com/green_sneddon.pdf"
    assert rec.extra.get("openalex_id") == "https://openalex.org/W123456789"

    # Verify per_page was capped at 100
    args, kwargs = mock_client.get.call_args
    assert kwargs["params"]["per_page"] <= 100


def test_arxiv_provider_atom_parsing_and_headers():
    atom_xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2101.12345v1</id>
    <published>2021-01-28T18:00:00Z</published>
    <title>   Analytical Bounds for Interaction of Multiple Cracks  </title>
    <summary> We present unified boundary integral solutions. </summary>
    <author><name>Alice Researcher</name></author>
    <author><name>Bob Colleague</name></author>
    <arxiv:doi>10.1007/s10704-021-9999-9</arxiv:doi>
    <link title="pdf" href="http://arxiv.org/pdf/2101.12345v1" type="application/pdf"/>
  </entry>
</feed>
"""
    mock_client = MagicMock(spec=HTTPClient)
    mock_client.get.return_value = HTTPResponse(
        status_code=200,
        headers={"Content-Type": "application/atom+xml"},
        content=atom_xml.encode("utf-8"),
    )

    prov = ArXivProvider(client=mock_client)
    records = prov.search("cracks", limit=5)

    assert len(records) == 1
    rec = records[0]
    assert rec.title == "Analytical Bounds for Interaction of Multiple Cracks"
    assert rec.arxiv_id == "2101.12345v1"
    # Clean normalized DOI, not the arXiv URL
    assert rec.doi == "10.1007/s10704-021-9999-9"
    assert rec.year == 2021
    assert rec.authors == ["Alice Researcher", "Bob Colleague"]
    assert rec.journal == "arXiv preprint"
    assert rec.oa_url == "http://arxiv.org/pdf/2101.12345v1"

    # Verify critical headers to avoid 406 Not Acceptable
    args, kwargs = mock_client.get.call_args
    headers = kwargs["headers"]
    assert headers["Accept"] == "*/*"
    assert "curl" in headers["User-Agent"]


def test_unpaywall_provider_parsing():
    mock_payload = {
        "doi": "10.1016/j.jmps.2020.104123",
        "is_oa": True,
        "oa_status": "gold",
        "title": "Exact Solutions for Penny-Shaped Cracks",
        "best_oa_location": {
            "url_for_pdf": "https://www.sciencedirect.com/article/pii/S002250962030369X/pdfft",
            "host_type": "publisher",
        },
    }
    mock_client = MagicMock(spec=HTTPClient)
    mock_client.get.return_value = HTTPResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b"",
    )
    mock_client.get.return_value._json = mock_payload

    prov = UnpaywallProvider(client=mock_client, email="test@mechanics.edu")
    oa_res = prov.find_oa("10.1016/j.jmps.2020.104123")

    assert oa_res.is_oa is True
    assert oa_res.oa_status == "gold"
    assert oa_res.pdf_url.endswith("/pdfft")
    assert oa_res.host_type == "publisher"
    assert oa_res.doi == "10.1016/j.jmps.2020.104123"


def test_semantic_scholar_provider_rate_limit_fallback():
    mock_client = MagicMock(spec=HTTPClient)
    # Simulate 429 rate limit
    mock_client.get.return_value = HTTPResponse(
        status_code=429,
        headers={},
        content=b'{"message": "Rate limit exceeded"}',
    )

    prov = SemanticScholarProvider(client=mock_client)
    # Must not raise an exception; falls back gracefully
    records = prov.search("penny shaped cracks", limit=10)
    assert records == []

