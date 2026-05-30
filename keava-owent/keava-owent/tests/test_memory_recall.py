"""
test_memory_recall.py — relational arrangement behaves, and the packing stub
stays a stub.
"""

import os
import tempfile
import pytest
from keava_owent.memory.graph import MemoryGraph
from keava_owent.memory.recall import Recall
from keava_owent.memory.arrangement.packing_geometry import PackingGeometryArrangement


def _mem():
    d = tempfile.mkdtemp()
    return MemoryGraph(os.path.join(d, "g.json"))


def test_relational_recall_walks_structure():
    m = _mem()
    m.add_node("a", "concept")
    m.add_node("b", "concept")
    m.add_node("c", "concept")
    m.add_edge("a", "b", "relates_to", weight=2.0)
    m.add_edge("b", "c", "supports", weight=1.0)
    r = Recall(m)
    near = r.related("a", budget=5)
    assert "b" in near        # directly related, strongest link
    assert "c" in near        # reachable by walking the structure


def test_isolated_node_is_a_gap():
    m = _mem()
    m.add_node("lonely", "concept")
    r = Recall(m)
    assert "lonely" in r.isolated_nodes()


def test_packing_geometry_is_held_open():
    # Open Problem 2: the packing-geometry strategy must remain an honest stub.
    strat = PackingGeometryArrangement()
    with pytest.raises(NotImplementedError):
        strat.neighbors(None, "x", 5)
