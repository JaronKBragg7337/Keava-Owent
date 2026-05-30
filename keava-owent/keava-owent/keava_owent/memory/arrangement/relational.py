"""
memory/arrangement/relational.py — the DEFAULT, proven strategy.

This is ordinary relational arrangement: nodes connected by typed edges,
retrieved by walking the relationships rather than scanning a list. It is
deliberately the *old, shipped* thing (Statement 2), because your own tests
(repo Section 7a) showed exactly this — structured arrangement beating a linear
list ~3x on clean recall, ~2x under moderate damage — reproduced by two
independent executors. We use the thing that was actually tested, and label it
as such. It carries the load while the packing-geometry question stays open.
"""

import networkx as nx
from .base import ArrangementStrategy


class RelationalArrangement(ArrangementStrategy):
    @property
    def name(self) -> str:
        return "relational"

    def link(self, graph: nx.MultiDiGraph, node_id) -> None:
        # Linking is driven by the edges the system asserts when it integrates
        # information (depends_on, supports, contradicts, ...). This strategy
        # does not impose extra geometry; it lets the relationship structure be
        # whatever the system has actually learned — emergence (Source 4's
        # companion principle), not a hand-authored layout.
        return None

    def neighbors(self, graph: nx.MultiDiGraph, node_id, budget: int) -> list:
        """Walk outward from a node, nearest relationships first.

        We use a breadth-first walk weighted by edge weight: the most strongly
        related nodes are returned first, up to the retrieval budget. This is the
        'walk the structure' retrieval that beat linear scanning in testing.
        """
        if node_id not in graph:
            return []
        seen = {node_id}
        ordered = []
        frontier = [node_id]
        while frontier and len(ordered) < budget:
            nxt = []
            # gather all outgoing and incoming neighbors of the frontier
            cand = []
            for n in frontier:
                for _, dst, data in graph.out_edges(n, data=True):
                    cand.append((data.get("weight", 1.0), dst))
                for src, _, data in graph.in_edges(n, data=True):
                    cand.append((data.get("weight", 1.0), src))
            # strongest relationships first
            cand.sort(key=lambda x: x[0], reverse=True)
            for _, node in cand:
                if node not in seen:
                    seen.add(node)
                    ordered.append(node)
                    nxt.append(node)
                    if len(ordered) >= budget:
                        break
            frontier = nxt
        return ordered[:budget]
