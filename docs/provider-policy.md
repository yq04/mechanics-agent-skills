# Academic Literature Provider Policies & Integration Protocols

> Snapshot Date: 2026-09-21  
> Purpose: Reference specifications for external academic APIs, rate limiting rules, authentication, and error recovery in Mechanics Agent Skills.

---

## 1. Overview & Policy Philosophy

Mechanics Agent Skills integrates multiple bibliographic and open-access data providers. To ensure reliability, reproducible science, and good academic citizenship, all provider interactions conform to the following policies:

1. **Polite Pool Compliance**: All requests supply valid identification and contact headers to route traffic through polite service queues.
2. **Deterministic Exponential Backoff**: Transient errors (HTTP 429, 500, 502, 503, 504) are handled with jittered exponential backoff rather than immediate aggressive retry loops.
3. **Local Caching First**: Responses are cached locally in SQLite (`~/.cache/mechanics_skills/` or run directories) to prevent redundant queries.

---

## 2. Crossref REST API

### 2.1 Endpoint & Authentication
- **Base URL**: `https://api.crossref.org/works`
- **Authentication**: Unauthenticated with mandatory polite pool headers.

### 2.2 Header & Etiquette Specification
- **User-Agent Format**: `MechanicsAgentSkills/3.1.0 (mailto:user@example.org)`
- **Polite Header**: The `mailto` header or query parameter routes traffic to Crossref's polite cluster, guaranteeing higher stability and throughput.

### 2.3 Rate Limits & Pagination
- **Rate Limit**: Typically 50 requests/second under the polite pool, with dynamic rate-limiting monitored via `X-Rate-Limit-Limit` and `X-Rate-Limit-Interval`.
- **429 Handling**: Automatically backs off using exponential delays: 1s, 2s, 4s, up to a maximum delay.
- **Deep Pagination**: Uses cursor-based pagination (`cursor=*`) for queries exceeding 1,000 results. Standard `offset` pagination is avoided for deep traversals due to server-side performance degradation.

### 2.4 Identifier Normalization
- All DOIs are normalized:
  - Trimmed of leading `https://doi.org/` or `http://dx.doi.org/`.
  - Converted to lowercase.
  - Stripped of surrounding whitespace and trailing punctuation (unless part of a valid DOI suffix).

---

## 3. OpenAlex REST API

### 3.1 Endpoint & Authentication
- **Base URL**: `https://api.openalex.org/`
- **Authentication**: Optional API key supported via `OPENALEX_API_KEY` environment variable.

### 3.2 Current Protocol Rules (August/September 2026 Snapshot)
- **Polite Pool Rate Limit**: Anonymous requests are strictly limited to **10 requests per second**. Supplying a valid email in `User-Agent` or an API key improves reliability and daily quota limits (10x budget).
- **Page Size Limits**: Hard limit of **`per_page <= 100`**. Any request specifying `per_page > 100` will be rejected or truncated by the API; client automatically bounds page size to 100.
- **Filter Constraints**: Maximum of **100 entities** in pipe-delimited `|` (OR) filter expressions.
- **Random Sample Limit**: Maximum sample size is **10,000**.
- **Pagination Boundary**:
  - Basic `page` numbering is supported only up to result index **10,000**.
  - Traversal beyond 10,000 records strictly requires cursor-based pagination (`cursor=*`).
- **HTTP Status Codes**:
  - `429 Too Many Requests`: Indicates momentary burst limit or daily budget exhaustion.
  - `403 Forbidden`: Treated as a permission or blocked client issue; does not enter an infinite retry loop.

---

## 4. arXiv Atom API

### 4.1 Endpoint & Protocol
- **Base URL**: `https://export.arxiv.org/api/query`
- **Protocol**: Enforces strict **HTTPS**. (Historical plain HTTP requests triggered HTTP 406 Not Acceptable errors on modern arXiv infrastructure).
- **Content-Type**: Receives and parses standard XML Atom responses.

### 4.2 Rate Limits & Scheduling
- **Frequency Rule**: Maximum of **1 query every 3 seconds** aggregated across all client threads.
- **Concurrency Rule**: Single active connection only. Parallel multi-threaded workers must route arXiv calls through a serialized internal queue.
- **Retry Strategy**: If arXiv returns HTTP 503 or transient rate limit errors, wait intervals must start at a minimum of 5 seconds.

### 4.3 Identifier Normalization
- Canonical format: `arXiv:YYMM.NNNNN` or legacy format `arXiv:arch-ive/YYMMNNN`.
- arXiv identifiers are maintained strictly in a dedicated field and never conflated with DOIs.

---

## 5. Semantic Scholar (S2) API

### 5.1 Endpoint & Authentication
- **Base URL**: `https://api.semanticscholar.org/graph/v1/`
- **Authentication**: Optional API key via `S2_API_KEY` header.

### 5.2 Rate Limits & Fallback
- Unauthenticated requests are subject to strict per-minute rate limits.
- S2 is used primarily as a secondary enrichment provider for citation graphs and OA link resolution when OpenAlex or Crossref records require additional corroboration.

---

## 6. Unpaywall REST API

### 6.1 Endpoint & Parameters
- **Base URL**: `https://api.unpaywall.org/v2/`
- **Mandatory Parameter**: `email=...` query parameter must be included on every request.

### 6.2 Open Access Resolution Protocol
- Locates `best_oa_location` record.
- Distinguishes direct PDF download links (`url_for_pdf`) from landing page URLs (`url_for_landing_page`).
- Only verified direct PDF streams are ingested into the evidence extraction pipeline; landing pages are flagged for human review or browser retrieval.
