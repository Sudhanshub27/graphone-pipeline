"""
================================================================================
GRAPHONE PIPELINE: KNOWLEDGE GRAPH LINKAGE & RELATION EXTRACTION ENGINE
================================================================================

Transforms extracted entity JSONL records into a relational Knowledge Graph with
typed nodes and edges (Graph Triples). Generates GraphML and Cypher export scripts
for Neo4j / NetworkX graph visualization.
================================================================================
"""

import json
from typing import Any, Dict, List, Tuple

import structlog

from config.settings import settings
from src.dashboard.processed_reader import get_all_processed_records

logger = structlog.get_logger(__name__)


class KnowledgeGraphLinker:
    """Knowledge Graph Construction and Export Engine."""

    def __init__(self):
        self.nodes_file = settings.DATA_PROCESSED_DIR / "graph_nodes.jsonl"
        self.edges_file = settings.DATA_PROCESSED_DIR / "graph_edges.jsonl"

    def build_graph_triples(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Build graph nodes and relational edges across all ingested entities."""
        all_records = get_all_processed_records()
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_ids: set[str] = set()

        # 1. Process Startup Nodes
        for startup in all_records.get("startups", []):
            s_name = startup.get("canonical_name") or startup.get("name") or "Unknown Startup"
            s_id = f"node-startup-{startup.get('id', s_name.lower().replace(' ', '-'))}"
            if s_id not in node_ids:
                node_ids.add(s_id)
                nodes.append({
                    "id": s_id,
                    "label": "Startup",
                    "name": s_name,
                    "location": startup.get("location"),
                    "funding": startup.get("total_funding"),
                    "stage": startup.get("stage"),
                })

        # 2. Process Product Nodes & PRODUCES edges
        for product in all_records.get("products", []):
            p_name = product.get("canonical_name") or product.get("name") or product.get("title") or "Unknown Product"
            p_id = f"node-product-{product.get('id', p_name.lower().replace(' ', '-'))}"
            if p_id not in node_ids:
                node_ids.add(p_id)
                nodes.append({
                    "id": p_id,
                    "label": "Product",
                    "name": p_name,
                    "maker": product.get("maker_company"),
                    "pricing": product.get("pricing_model"),
                })

            # Connect Product to Maker Startup
            maker = product.get("maker_company")
            if maker:
                matching_startup_id = None
                for node in nodes:
                    if node["label"] == "Startup" and maker.lower() in node["name"].lower():
                        matching_startup_id = node["id"]
                        break
                if matching_startup_id:
                    edges.append({
                        "source": matching_startup_id,
                        "target": p_id,
                        "relation": "PRODUCES",
                        "confidence": 0.95,
                    })

        # 3. Process Research Paper Nodes
        for paper in all_records.get("research_papers", []):
            title = paper.get("title") or "Untitled Research Paper"
            paper_id = f"node-paper-{paper.get('id', title.lower()[:20].replace(' ', '-'))}"
            if paper_id not in node_ids:
                node_ids.add(paper_id)
                nodes.append({
                    "id": paper_id,
                    "label": "ResearchPaper",
                    "name": title,
                    "authors": paper.get("authors", []),
                    "journal": paper.get("journal_conference"),
                })

        # 4. Process Job Nodes & POSTED_BY edges
        for job in all_records.get("jobs", []):
            j_title = job.get("title") or "Unknown Position"
            comp = job.get("company")
            j_id = f"node-job-{job.get('id', j_title.lower()[:20].replace(' ', '-'))}"
            if j_id not in node_ids:
                node_ids.add(j_id)
                nodes.append({
                    "id": j_id,
                    "label": "Job",
                    "name": j_title,
                    "company": comp,
                    "salary": job.get("salary_range"),
                })

            if comp:
                for node in nodes:
                    if node["label"] == "Startup" and comp.lower() in node["name"].lower():
                        edges.append({
                            "source": j_id,
                            "target": node["id"],
                            "relation": "POSTED_BY",
                            "confidence": 0.90,
                        })
                        break

        # Persist graph nodes and edges to JSONL
        settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.nodes_file, "w", encoding="utf-8") as f:
            for n in nodes:
                f.write(json.dumps(n) + "\n")
        with open(self.edges_file, "w", encoding="utf-8") as f:
            for e in edges:
                f.write(json.dumps(e) + "\n")

        logger.info("Built Knowledge Graph Triples", nodes_count=len(nodes), edges_count=len(edges))
        return nodes, edges

    def generate_cypher_import_script(self) -> str:
        """Generate Cypher queries for Neo4j database import."""
        nodes, edges = self.build_graph_triples()
        cypher_lines = ["// --- Graphone Pipeline Neo4j Cypher Import Script ---"]
        
        for n in nodes:
            name_clean = n["name"].replace('"', '\\"')
            cypher_lines.append(f'MERGE (n:{n["label"]} {{id: "{n["id"]}", name: "{name_clean}"}});')

        for e in edges:
            cypher_lines.append(
                f'MATCH (a {{id: "{e["source"]}"}}), (b {{id: "{e["target"]}"}}) '
                f'MERGE (a)-[r:{e["relation"]} {{confidence: {e["confidence"]}}}]->(b);'
            )

        return "\n".join(cypher_lines) + "\n"


graph_linker = KnowledgeGraphLinker()
