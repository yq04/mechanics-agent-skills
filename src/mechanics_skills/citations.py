"""
Citation snowballing, Main Path Analysis (SPC), and Mermaid diagram visualization.
"""

from collections import defaultdict, deque
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from mechanics_skills.identifiers import normalize_doi
from mechanics_skills.providers.openalex import OpenAlexProvider


def snowball_citations(
    seed_dois: List[str],
    max_depth: int = 2,
    max_papers_per_hop: int = 15,
    direction: str = "both",  # "backward", "forward", or "both"
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Multi-hop BFS citation snowballing via OpenAlex.
    Traverses backward (references) and forward (citing papers).
    Returns graph dictionary with nodes and edges.
    """
    openalex = OpenAlexProvider(client=client)

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str]] = set()

    clean_seeds = [normalize_doi(d) or d.lower().strip() for d in seed_dois if d.strip()]

    queue: deque = deque()
    for s in clean_seeds:
        queue.append((s, 0))

    while queue:
        current_doi, depth = queue.popleft()
        if depth >= max_depth:
            continue

        work = openalex.get_work(current_doi)
        if not work or not work.get("id"):
            continue

        work_id = work.get("id")
        work_doi = normalize_doi(work.get("doi")) or current_doi
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in work.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]

        if work_doi not in nodes:
            nodes[work_doi] = {
                "doi": work_doi,
                "title": work.get("title") or "Untitled",
                "year": work.get("publication_year"),
                "authors": authors,
                "citations": work.get("cited_by_count", 0),
                "openalex_id": work_id,
            }

        # 1. Backward snowballing (references)
        if direction in ("backward", "both"):
            ref_ids = work.get("referenced_works", [])
            if ref_ids:
                sample_refs = ref_ids[:max_papers_per_hop]
                ref_works = openalex.batch_lookup("works", sample_refs, id_field="openalex_id")
                for rw in ref_works:
                    r_doi = normalize_doi(rw.get("doi")) or rw.get("id", "").split("/")[-1]
                    if not r_doi:
                        continue
                    r_auth = [
                        a.get("author", {}).get("display_name", "")
                        for a in rw.get("authorships", [])
                        if a.get("author", {}).get("display_name")
                    ]
                    if r_doi not in nodes:
                        nodes[r_doi] = {
                            "doi": r_doi,
                            "title": rw.get("title") or "Untitled",
                            "year": rw.get("publication_year"),
                            "authors": r_auth,
                            "citations": rw.get("cited_by_count", 0),
                            "openalex_id": rw.get("id"),
                        }
                    edge_key = (work_doi, r_doi)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({
                            "citing": work_doi,
                            "cited": r_doi,
                            "depth": depth + 1,
                            "direction": "backward",
                        })
                    if depth + 1 < max_depth:
                        queue.append((r_doi, depth + 1))

        # 2. Forward snowballing (citations)
        if direction in ("forward", "both") and work_id:
            clean_oa_id = work_id.split("/")[-1]
            cites_res = openalex.search_works(
                filter_params={"cites": clean_oa_id},
                sort="cited_by_count:desc",
                per_page=min(max_papers_per_hop, 50),
            )
            for cw in cites_res.get("results", []):
                c_doi = normalize_doi(cw.get("doi")) or cw.get("id", "").split("/")[-1]
                if not c_doi:
                    continue
                c_auth = [
                    a.get("author", {}).get("display_name", "")
                    for a in cw.get("authorships", [])
                    if a.get("author", {}).get("display_name")
                ]
                if c_doi not in nodes:
                    nodes[c_doi] = {
                        "doi": c_doi,
                        "title": cw.get("title") or "Untitled",
                        "year": cw.get("publication_year"),
                        "authors": c_auth,
                        "citations": cw.get("cited_by_count", 0),
                        "openalex_id": cw.get("id"),
                    }
                edge_key = (c_doi, work_doi)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "citing": c_doi,
                        "cited": work_doi,
                        "depth": depth + 1,
                        "direction": "forward",
                    })
                if depth + 1 < max_depth:
                    queue.append((c_doi, depth + 1))

    return {
        "seed_dois": clean_seeds,
        "max_depth": max_depth,
        "nodes": nodes,
        "edges": edges,
    }


def compute_spc_weights(
    nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]
) -> Dict[Tuple[str, str], int]:
    """
    Search Path Count (SPC) algorithm (Hummon & Doreian 1989, Batagelj 2003).
    Knowledge flow DAG: edge from cited (source/earlier) to citing (sink/later).
    Edge SPC = (number of paths from sources to u) * (number of paths from v to sinks).
    """
    adj: Dict[str, List[str]] = defaultdict(list)
    rev_adj: Dict[str, List[str]] = defaultdict(list)
    in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}
    out_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}

    flow_edges: List[Tuple[str, str]] = []
    for e in edges:
        cited = e.get("cited") or e.get("source") or ""
        citing = e.get("citing") or e.get("target") or ""
        if cited in nodes and citing in nodes:
            flow_edges.append((cited, citing))
            adj[cited].append(citing)
            rev_adj[citing].append(cited)
            in_degree[citing] = in_degree.get(citing, 0) + 1
            out_degree[cited] = out_degree.get(cited, 0) + 1

    if not flow_edges:
        return {}

    temp_in = dict(in_degree)
    zero_in = [n for n, deg in temp_in.items() if deg == 0]
    topo_order: List[str] = []

    while zero_in:
        curr = zero_in.pop(0)
        topo_order.append(curr)
        for nxt in adj.get(curr, []):
            temp_in[nxt] -= 1
            if temp_in[nxt] == 0:
                zero_in.append(nxt)

    for n in nodes:
        if n not in topo_order:
            topo_order.append(n)

    n_sources: Dict[str, int] = defaultdict(int)
    for n in topo_order:
        parents = rev_adj.get(n, [])
        if not parents:
            n_sources[n] = 1
        else:
            n_sources[n] = sum(n_sources[p] for p in parents)

    n_sinks: Dict[str, int] = defaultdict(int)
    for n in reversed(topo_order):
        children = adj.get(n, [])
        if not children:
            n_sinks[n] = 1
        else:
            n_sinks[n] = sum(n_sinks[c] for c in children)

    spc_weights: Dict[Tuple[str, str], int] = {}
    for cited, citing in flow_edges:
        spc = n_sources[cited] * n_sinks[citing]
        spc_weights[(cited, citing)] = spc

    return spc_weights


def extract_main_path(
    citation_network: Dict[str, Any], top_k: int = 1
) -> List[List[Dict[str, Any]]]:
    """
    Extract the main path (backbone) of scientific lineage using SPC weights.
    Returns list of paths, each path being an ordered list of node dicts.
    """
    nodes = citation_network.get("nodes", {})
    edges = citation_network.get("edges", [])
    if not nodes or not edges:
        return []

    spc_weights = compute_spc_weights(nodes, edges)
    if not spc_weights:
        return []

    flow_adj: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    in_degree: Dict[str, int] = {n: 0 for n in nodes}

    for (cited, citing), spc in spc_weights.items():
        flow_adj[cited].append((citing, spc))
        in_degree[citing] = in_degree.get(citing, 0) + 1

    sources = [n for n in nodes if in_degree.get(n, 0) == 0 and flow_adj.get(n)]
    if not sources:
        sources = list(nodes.keys())

    main_paths: List[List[Dict[str, Any]]] = []

    def source_score(s: str) -> int:
        outgoing = flow_adj.get(s, [])
        return max([w for _, w in outgoing], default=0)

    sorted_sources = sorted(sources, key=source_score, reverse=True)

    for src in sorted_sources[:top_k]:
        node_dict = dict(nodes[src])
        node_dict['_node_id'] = src
        path = [node_dict]
        curr = src
        visited = {curr}

        while True:
            outgoing = [
                (nxt, w) for nxt, w in flow_adj.get(curr, []) if nxt not in visited
            ]
            if not outgoing:
                break
            outgoing.sort(key=lambda x: x[1], reverse=True)
            best_next, _ = outgoing[0]
            visited.add(best_next)
            next_dict = dict(nodes[best_next])
            next_dict['_node_id'] = best_next
            path.append(next_dict)
            curr = best_next

        if len(path) > 1:
            main_paths.append(path)

    return main_paths


def _sanitize_mermaid_id(raw_id: str) -> str:
    """Sanitize identifier for safe use as a Mermaid node ID."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)
    if not clean or clean[0].isdigit():
        clean = "P_" + clean
    return clean[:30]


def _extract_surname(raw_author: str) -> str:
    """Extract author surname handling both 'Surname, Initial' and 'Surname Initial'."""
    if not raw_author:
        return "Unknown"
    if "," in raw_author:
        return raw_author.split(",")[0].strip()
    parts = raw_author.split()
    if len(parts) >= 2 and len(parts[-1]) <= 3 and parts[-1].isupper():
        return parts[0]
    return parts[-1]


def generate_mermaid_citation_network(
    graph_data: Dict[str, Any],
    highlight_main_path: bool = True,
    max_nodes: int = 25,
) -> str:
    """
    Generate clean, publication-ready Mermaid flowchart for citation networks.
    Organizes papers chronologically into era subgraphs and highlights the main path.
    """
    nodes = graph_data.get("nodes", {})
    edges = graph_data.get("edges", [])

    if not nodes:
        return "flowchart TD\n    empty[No citation data available]"

    sorted_node_keys = sorted(
        nodes.keys(),
        key=lambda k: (nodes[k].get("citations") or 0),
        reverse=True,
    )[:max_nodes]
    selected_set = set(sorted_node_keys)

    main_path_nodes: Set[str] = set()
    main_path_edges: Set[Tuple[str, str]] = set()
    if highlight_main_path:
        paths = extract_main_path(graph_data, top_k=1)
        if paths:
            first_path = paths[0]
            for p in first_path:
                doi = p.get("doi")
                if doi:
                    main_path_nodes.add(doi)
                    selected_set.add(doi)
            for i in range(len(first_path) - 1):
                u = first_path[i].get("doi")
                v = first_path[i + 1].get("doi")
                if u and v:
                    main_path_edges.add((u, v))

    eras: Dict[str, List[str]] = defaultdict(list)
    for k in selected_set:
        if k not in nodes:
            continue
        year = nodes[k].get("year")
        if not year:
            era_label = "Undated"
        elif year < 1990:
            era_label = "Pre-1990 Foundations"
        elif year < 2005:
            era_label = "1990 - 2004 Classical Advances"
        elif year < 2018:
            era_label = "2005 - 2017 Modern Formulations"
        else:
            era_label = "2018 - Present Recent Frontiers"
        eras[era_label].append(k)

    lines: List[str] = [
        "flowchart TD",
        "    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;",
        "    classDef mainPath fill:#ffeb3b,stroke:#f57c00,stroke-width:3px,font-weight:bold;",
        "    classDef seedNode fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;",
    ]

    seed_set = set(graph_data.get("seed_dois", []))

    era_order = [
        "Pre-1990 Foundations",
        "1990 - 2004 Classical Advances",
        "2005 - 2017 Modern Formulations",
        "2018 - Present Recent Frontiers",
        "Undated",
    ]

    for era in era_order:
        if era not in eras:
            continue
        sub_id = _sanitize_mermaid_id(era)
        lines.append(f'    subgraph {sub_id} ["{era}"]')
        for k in eras[era]:
            node_info = nodes[k]
            nid = _sanitize_mermaid_id(k)
            first_author = "Unknown"
            if node_info.get("authors"):
                first_author = _extract_surname(node_info["authors"][0])
            year_str = str(node_info.get("year") or "n.d.")
            raw_title = node_info.get("title") or "Paper"
            clean_title = raw_title.replace('"', "'").replace(chr(10), " ").strip()
            if len(clean_title) > 35:
                clean_title = clean_title[:32] + "..."
            cites = node_info.get("citations", 0)

            label = f"{first_author} ({year_str})<br/>{clean_title}<br/>[Cites: {cites}]"
            lines.append(f'        {nid}["{label}"]')
        lines.append("    end")

    rendered_edges = 0
    for e in edges:
        cited = e.get("cited") or e.get("source")
        citing = e.get("citing") or e.get("target")
        if cited in selected_set and citing in selected_set:
            u_id = _sanitize_mermaid_id(cited)
            v_id = _sanitize_mermaid_id(citing)
            if (cited, citing) in main_path_edges:
                lines.append(f"    {u_id} ==>|main path| {v_id}")
            else:
                lines.append(f"    {u_id} --> {v_id}")
            rendered_edges += 1
            if rendered_edges >= 40:
                break

    for k in selected_set:
        nid = _sanitize_mermaid_id(k)
        if k in main_path_nodes:
            lines.append(f"    class {nid} mainPath;")
        elif k in seed_set:
            lines.append(f"    class {nid} seedNode;")

    return "\n".join(lines)




