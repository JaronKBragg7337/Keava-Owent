"""
memory/arrangement/packing_geometry.py — OPEN PROBLEM 2, held open on purpose.

This is Statement 4 of the four-statement separation rendered as code: applying
the planar unit-distance packing geometry to memory arrangement is UNBUILT.
Nobody has done it. The math is real and verified (OpenAI's May 20 2026 disproof
of square-grid optimality for the Erdos unit-distance problem; Will Sawin's
explicit lower bound, exponent delta >= 0.014, using the symmetries of a deep
algebraic number field / infinite class field towers). But the math being real
does not tell you how to map its neighbor-relationship structure onto memory
addressing — that mapping does not yet exist.

We keep this as a documented stub rather than mislabeling the ordinary
relational graph as "the spatial-arrangement layer." That mislabel is precisely
the demotion the project is built to avoid: a working graph quietly becoming the
reason the open question dies.

What would close it (the bar, stated honestly): a concrete mapping from the
unit-distance construction's relational geometry onto memory linking, PLUS an
experiment showing it beats ordinary relational arrangement on recall and
damage-resistance — the same bar the ~3x relational result already cleared,
applied to the new geometry.
"""

from .base import ArrangementStrategy


class PackingGeometryArrangement(ArrangementStrategy):
    @property
    def name(self) -> str:
        return "packing_geometry (UNBUILT)"

    def _not_built(self):
        raise NotImplementedError(
            "Applying unit-distance packing geometry to memory arrangement is "
            "UNBUILT (Open Problem 2). The math is verified real; the mapping to "
            "memory is not. This stub is kept deliberately empty so the open "
            "question stays open rather than being faked by the relational graph. "
            "Use RelationalArrangement until a real mapping is built and shown to "
            "beat it on recall and damage-resistance."
        )

    def link(self, graph, node_id) -> None:
        self._not_built()

    def neighbors(self, graph, node_id, budget: int) -> list:
        self._not_built()
