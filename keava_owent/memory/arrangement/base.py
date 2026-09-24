"""
memory/arrangement/base.py — the ArrangementStrategy interface.

This file exists to PROTECT the four-statement separation from Source 4 in code,
so it cannot quietly collapse the way it did once before in a model hand-off.
The four statements, kept distinct on purpose:

  1. Reaching toward a non-linear memory medium is OLD (Jaron's, longstanding).
  2. Relational / graph memory is OLD and already in production (NOT a discovery).
  3. The planar unit-distance packing math is NEW and verified real
     (OpenAI, May 20 2026; Will Sawin refined it to exponent delta >= 0.014,
     configurations exceeding n^1.014 unit-distance pairs).
  4. APPLYING that packing geometry to memory arrangement is UNBUILT — nobody
     has done it.

The real target named here is RELATIONAL GEOMETRY: maximizing meaningful
neighbor-relationships per unit of structure — explicitly NOT density or
"cramming more in." Two strategies implement this interface:
  - RelationalArrangement (DEFAULT, proven: structured arrangement beat a linear
    list ~3x on clean recall and ~2x under moderate damage in your own tests).
  - PackingGeometryArrangement (STUB: raises NotImplementedError; it is the
    open research question, held open rather than faked).
"""

from abc import ABC, abstractmethod


class ArrangementStrategy(ABC):
    """How memory nodes are arranged relative to one another for retrieval.

    The arrangement is the storage: meaning lives in how pieces sit in relation
    to each other, not in a sequence read top to bottom.
    """

    @abstractmethod
    def link(self, graph, node_id) -> None:
        """Decide and create the relationships a new node should have."""

    @abstractmethod
    def neighbors(self, graph, node_id, budget: int) -> list:
        """Return the most relationally-relevant nodes within a retrieval budget."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...
