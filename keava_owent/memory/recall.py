"""
memory/recall.py — relational retrieval over the graph.

Recall walks the structure (via the arrangement strategy) instead of scanning a
linear list. This is the retrieval path that, in your own tests, beat linear
storage ~3x on clean recall. It also surfaces the absence of relationships,
which the spark generator reads as a knowledge gap.
"""


class Recall:
    def __init__(self, memory):
        self.memory = memory

    def related(self, node_id: str, budget: int = 12) -> list:
        """Return nodes relationally near `node_id`, strongest links first."""
        return self.memory.strategy.neighbors(self.memory.g, node_id, budget)

    def isolated_nodes(self) -> list:
        """Nodes with no relationships at all.

        An isolated node is a piece of knowledge the system holds but hasn't
        connected to anything — a relational gap. The spark generator turns
        these into goals: 'go relate this to what you know.'
        """
        out = []
        for n in self.memory.g.nodes:
            deg = self.memory.g.degree(n)
            if deg == 0:
                out.append(n)
        return out
