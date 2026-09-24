"""
memory/graph.py — the relational memory substrate (Source 4).

Memory is held as a property graph: nodes are the things the system knows
(files, concepts, tasks, decisions, risks, dependencies) and edges are the typed
relationships between them. The arrangement IS the storage — meaning lives in how
the pieces sit relative to one another, retrieved by walking relationships rather
than reading a list top to bottom.

The graph is persisted as JSON so it survives restarts (continuity), and the
*arrangement strategy* is pluggable so the proven relational approach can later
be swapped for packing geometry without rearchitecting.
"""

import os
import json
import networkx as nx

from .arrangement.relational import RelationalArrangement
from ..store.db import utc_now_iso

NODE_TYPES = {"file", "concept", "task", "decision", "risk", "dependency"}
EDGE_TYPES = {
    "depends_on", "contradicts", "supports", "duplicates",
    "blocks", "updates", "relates_to",
}


class MemoryGraph:
    def __init__(self, path: str, strategy=None):
        self.path = path
        self.g = nx.MultiDiGraph()
        # Default to the PROVEN relational strategy. Swappable for the (open)
        # packing-geometry strategy later — same interface, no rearchitecting.
        self.strategy = strategy or RelationalArrangement()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                self.g = nx.node_link_graph(data, multigraph=True, directed=True)
            except Exception:
                # If the snapshot is unreadable we start clean rather than crash;
                # continuity favors a working empty graph over a dead process.
                self.g = nx.MultiDiGraph()

    def save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        data = nx.node_link_data(self.g)
        with open(self.path, "w") as f:
            json.dump(data, f)

    def add_node(self, node_id: str, node_type: str, payload: dict = None) -> None:
        if node_type not in NODE_TYPES:
            raise ValueError(f"node_type must be one of {sorted(NODE_TYPES)}")
        if node_id not in self.g:
            self.g.add_node(
                node_id, type=node_type, payload=payload or {},
                created=utc_now_iso(), last_touched=utc_now_iso(),
            )
        else:
            self.g.nodes[node_id]["last_touched"] = utc_now_iso()
        self.strategy.link(self.g, node_id)

    def add_edge(self, src: str, dst: str, edge_type: str, weight: float = 1.0) -> None:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"edge_type must be one of {sorted(EDGE_TYPES)}")
        # Reinforce an existing edge rather than duplicating it: repeated
        # assertion of the same relationship strengthens it (a small nod to
        # emergence — structure that grows through use, Source 4 companion).
        for _, d, k, data in self.g.out_edges(src, keys=True, data=True):
            if d == dst and data.get("type") == edge_type:
                data["weight"] = data.get("weight", 1.0) + weight
                return
        self.g.add_edge(src, dst, type=edge_type, weight=weight, created=utc_now_iso())

    def has(self, node_id: str) -> bool:
        return node_id in self.g

    def all_node_ids(self) -> list:
        return list(self.g.nodes)

    def node(self, node_id: str) -> dict:
        return dict(self.g.nodes[node_id]) if node_id in self.g else None
