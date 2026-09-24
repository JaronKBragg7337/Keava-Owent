"""
spark/generator.py — the self-generated spark (Source 1, instance B).

The whole project began from one requirement: a system that, when given nothing,
finds something — that doesn't sit idle waiting for a human to hand it a task.
Source 1's instance B names the resolution precisely: a goal that waits for an
external spark has outsourced its own trigger; instead, let the trigger come from
a gap in the system's OWN knowledge. The not-knowing becomes the spark.

So this generator reads the memory graph for gaps and turns them into goals. It
never returns "nothing to do" while the standing condition is unsatisfied —
there is always either a gap to close or, failing that, the baseline goal of
reporting honestly to the human and asking what matters next.
"""

from ..store.db import utc_now_iso


class SparkGenerator:
    def __init__(self, recall):
        self.recall = recall

    def find_gaps(self, state) -> list:
        """Identify gaps in the system's own knowledge.

        Two kinds of gap for the v1 skeleton:
          1. Isolated nodes: knowledge held but unconnected to anything. The gap
             is 'I know this but don't know how it relates.'
          2. Stale references: a live source the system couldn't read fresh. The
             gap is 'I can't currently see something I'm supposed to track.'
        """
        gaps = []
        for node_id in self.recall.isolated_nodes():
            gaps.append({
                "kind": "unconnected_knowledge",
                "about": node_id,
                "found_at": utc_now_iso(),
            })
        for src in state.stale_sources:
            gaps.append({
                "kind": "stale_reference",
                "about": src,
                "found_at": utc_now_iso(),
            })
        return gaps

    def next_goal(self, gaps: list, state) -> dict:
        """Choose the next goal. There is always one.

        If there are gaps, the highest-priority gap becomes the goal (a stale
        reference outranks unconnected knowledge, because being unable to SEE a
        live condition is more urgent than not having related a fact yet). If
        there are no gaps at all, the baseline goal is to report the honest
        ledger to the human and ask what matters next — which keeps the loop
        oriented to 'earn my keep' rather than busy-work, and feeds the human
        verdict log that the contribution slot depends on.
        """
        stale = [g for g in gaps if g["kind"] == "stale_reference"]
        if stale:
            g = stale[0]
            return {
                "kind": "restore_reference",
                "intent": f"regain a live reading of {g['about']}",
                "about": g["about"],
            }
        unconnected = [g for g in gaps if g["kind"] == "unconnected_knowledge"]
        if unconnected:
            g = unconnected[0]
            return {
                "kind": "relate_knowledge",
                "intent": f"relate {g['about']} to existing knowledge",
                "about": g["about"],
            }
        # No gaps: the baseline never-idle goal. Report honestly and invite
        # direction. This is email's natural job (the transport layer).
        return {
            "kind": "report_and_ask",
            "intent": "report the honest ledger to the human and ask what matters next",
            "about": None,
        }
