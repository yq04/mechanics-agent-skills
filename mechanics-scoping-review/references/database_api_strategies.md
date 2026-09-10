# Mechanics Database API Strategies & Rate-Limiting Policy

## 1. Overview of Open Scientific Databases for Mechanics

Solid mechanics and fracture mechanics require access to historical classics (1960s-1990s) and modern developments (2000s-present) published in Elsevier, Springer, ASME, Taylor & Francis, and Oxford journals. Biomedical databases (PubMed) have near-zero coverage of these domains. This skill uses four primary open APIs:

| Database | Primary Role | Rate Limit / Quota | Key Features |
|---|---|---|---|
| **Crossref REST API** | Official DOI Registry & Metadata Authority | Free, polite pool with `mailto` header (~50 req/sec) | Direct publication dates, complete journal containers, publisher DOIs |
| **OpenAlex API** | Global Scholarly Knowledge Graph (250M+ works) | Free, polite pool with `mailto` header (100k req/day) | Reconstructed abstracts, full citation graph (`referenced_works`, `cites`), concept filtering |
| **arXiv API** | Mechanics, Applied Math & Mathematical Physics Preprints | Free, rate-limited to 1 request per 3 seconds | Full text and abstract access for recent preprints |
| **Semantic Scholar API** | Citation & Influential Reference Analytics | Public API (rate-limited / occasional 429 on shared IPs) | High-quality citation influence scores, fallback for OpenAlex |
| **Unpaywall API** | Legal Open Access Full-Text PDF Retrieval | Free with `email` parameter (100k req/day) | Direct PDF URLs from institutional repositories, bronze/gold OA |

## 2. Multi-Backend Fallback Architecture

To guarantee 100% retrieval reliability even under temporary rate limits:
1. **Search Phase**: Crossref and OpenAlex are queried in parallel. arXiv is queried for recent mathematical physics developments. Results are merged and deduplicated by lowercase DOI.
2. **Citation Graph Phase**: OpenAlex is used as the primary engine for both backward references and forward citations. If OpenAlex is unavailable, Crossref reference lists are parsed.
3. **Full-Text Retrieval**: Unpaywall is checked first for legitimate publisher/repository OA links. If not found, OpenAlex OA location is checked.