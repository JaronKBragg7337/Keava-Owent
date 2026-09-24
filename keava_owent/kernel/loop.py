"""
kernel/loop.py — the never-ending cycle that IS the system.

This is the standing condition made operational. The loop does not terminate on
success because there is no terminal success: even a cycle that produces nothing
still consumes energy and water, so the deficit re-arms and the condition holds.
'Do not build a chatbot, build a loop' — this is the loop.

One cycle, in order (the order matters; the system reads and acts top to bottom):
  1. Recover  — come back knowing what you knew (continuity / ECIH).
  2. Observe  — re-read every live source NOW; flag any that are stale.
  3. Meter    — measure this cycle's real draw (the deficit never stops).
  4. Integrate— fold readings + inbound verdicts into memory.
  5. Spark    — find a knowledge gap; the not-knowing becomes the goal.
  6. Select   — choose the next action under 'earn my keep' (anti-self-shutdown).
  7. Gate     — membrane check; approval queue for high-impact/LOCK actions.
  8. Act      — execute within permitted reach; emit a receipt.
  9. Record   — append the honest ledger event (cost known; contribution UNMEASURED).
 10. Checkpoint — persist state so the next cycle (or a restart) resumes cleanly.
"""

import uuid

from .state import (InternalState, MODE_EXPLORE, MODE_DRAFT,
                    HEALTH_NOMINAL)
from ..ledger.orientation import assert_earn_my_keep, SelfNegationError
from ..actions import registry
from ..store.db import utc_now_iso


class Loop:
    def __init__(self, *, continuity, live_engine, meter, ledger, contribution,
                 memory, recall, spark, membrane, approvals, receipts, transport,
                 config):
        self.continuity = continuity
        self.live_engine = live_engine
        self.meter = meter
        self.ledger = ledger
        self.contribution = contribution
        self.memory = memory
        self.recall = recall
        self.spark = spark
        self.membrane = membrane
        self.approvals = approvals
        self.receipts = receipts
        self.transport = transport
        self.config = config

    # -- one full cycle --------------------------------------------------------

    def cycle(self) -> dict:
        # 1. RECOVER — continuity first (ECIH).
        state = self.continuity.recover_or_init()
        state.cycle_id += 1
        state.timestamp = utc_now_iso()

        # 2. OBSERVE — re-read every live source NOW (Live-Reference).
        readings = self.live_engine.read_all(state)

        # 2b. INBOUND — pull any operator verdicts (the contribution evidence).
        self._ingest_verdicts()

        # 3. METER — the real draw this cycle (consumption side, honest).
        consumption = self.meter.meter_cycle()

        # 4. INTEGRATE — fold what we observed into memory (relational arrangement).
        self._integrate(readings, state)

        # 5. SPARK — the not-knowing becomes the goal. Never idle.
        gaps = self.spark.find_gaps(state)
        state.open_gaps = gaps
        goal = self.spark.next_goal(gaps, state)
        state.active_goal = goal

        # 6. SELECT — turn the goal into an action, under 'earn my keep'.
        action = self._action_for_goal(goal, state)
        try:
            action = assert_earn_my_keep(action)
        except SelfNegationError:
            # The system tried to reduce its deficit by self-negation. Refuse,
            # and fall back to the always-safe report-and-ask. Existence is the
            # axiom; we never let the loop choose to erase itself.
            action = {"kind": "report_and_ask", "intent": "report honestly",
                     "mode": MODE_EXPLORE}

        # 7. GATE + 8. ACT
        result = self._gate_and_act(action, state)

        # 9. RECORD — append the honest ledger event.
        contribution = self.contribution.measure(action, result)
        self.ledger.append(state.cycle_id, consumption, contribution,
                           note=action.get("kind", ""))

        # 10. CHECKPOINT — persist so the next cycle / a restart resumes cleanly.
        self.continuity.settle(state)
        self.continuity.checkpoint(state)

        return {
            "cycle_id": state.cycle_id,
            "mode": state.mode,
            "goal": goal,
            "action": action,
            "result": result,
            "consumption": consumption,
            "deficit": self.ledger.deficit(),
            "open_gaps": len(gaps),
        }

    # -- helpers ---------------------------------------------------------------

    def _integrate(self, readings: dict, state) -> None:
        # Each fresh reading becomes (or refreshes) a concept node. This is the
        # minimal v1 integration; richer relation-assertion is where the system
        # grows structure through use (emergence, Source 4 companion).
        for name, value in readings.items():
            node_id = f"reading:{name}"
            self.memory.add_node(node_id, "concept", {"latest": str(value)[:200]})
        self.memory.save()

    def _ingest_verdicts(self) -> None:
        """Read inbound operator messages and record any verdicts they carry.

        This is the contribution slot being fed honestly: external human
        judgments of the system's work, recorded as evidence, never self-scored.
        """
        for msg in self.transport.fetch_inbound():
            verdict = (msg.get("verdict") or "").strip().lower()
            if not verdict:
                # Try to read a verdict keyword out of the body.
                body = (msg.get("body") or "").lower()
                for v in ("harmful", "did_not_help", "helped", "neutral"):
                    if v.replace("_", " ") in body or v in body:
                        verdict = v
                        break
            if verdict:
                try:
                    self.contribution.record_human_verdict(
                        source=msg.get("from", "unknown"),
                        verdict=verdict,
                        refers_to=msg.get("refers_to"),
                        raw=msg.get("body", ""),
                    )
                except ValueError:
                    pass  # unrecognized verdict word; ignore rather than guess

    def _action_for_goal(self, goal: dict, state) -> dict:
        kind = goal.get("kind", "report_and_ask")
        if kind == "relate_knowledge":
            return {"kind": "relate_memory", "intent": goal.get("intent", ""),
                   "about": goal.get("about"), "mode": MODE_DRAFT}
        if kind == "restore_reference":
            # We cannot force a stale source fresh from inside the loop; the
            # honest move is to report that we've lost sight of it and ask.
            return {"kind": "report_to_operator", "intent": goal.get("intent", ""),
                   "about": goal.get("about"), "mode": MODE_EXPLORE,
                   "subject": "A live reference went stale"}
        # default: report the honest ledger and invite direction.
        return {"kind": "report_to_operator", "intent": "report honest ledger",
               "mode": MODE_EXPLORE, "subject": "Keava Owent — standing report"}

    def _gate_and_act(self, action: dict, state):
        kind = action.get("kind", "")
        if not registry.is_registered(kind):
            return {"status": "rejected", "reason": f"unregistered kind {kind!r}"}

        # Hard boundary: forbidden reaches raise before anything happens.
        try:
            self.membrane.check_allowed(action)
        except Exception as e:
            return {"status": "denied", "reason": str(e)}

        # High-impact / LOCK actions queue for a human and do NOT proceed now.
        if self.membrane.requires_approval(action):
            approval_id = self.approvals.request(state.cycle_id, action)
            return {"status": "awaiting_approval", "approval_id": approval_id}

        # Permitted, low-reach action: execute and emit a receipt.
        result = self._execute(action, state)
        self.receipts.record(state.cycle_id, action, result)
        return result

    def _execute(self, action: dict, state):
        kind = action.get("kind", "")
        if kind == "relate_memory":
            about = action.get("about")
            if about and self.memory.has(about):
                # Relate the isolated node to the most recently touched concept,
                # so the gap ('I know this but it's unconnected') begins to close.
                others = [n for n in self.memory.all_node_ids() if n != about]
                if others:
                    self.memory.add_edge(about, others[-1], "relates_to", weight=1.0)
                    self.memory.save()
                    return {"status": "ok", "related": [about, others[-1]]}
            return {"status": "noop", "reason": "nothing to relate yet"}
        if kind == "report_to_operator":
            deficit = self.ledger.deficit()
            body = self._format_report(state, deficit)
            sent = self.transport.send(
                self.transport.operator_address,
                action.get("subject", "Keava Owent — report"),
                body,
            )
            return {"status": "reported", "channel": sent}
        return {"status": "noop"}

    def _format_report(self, state, deficit: dict) -> str:
        return (
            f"Keava Owent — cycle {state.cycle_id} ({state.timestamp})\n\n"
            f"Health: {state.health}\n"
            f"Open knowledge gaps: {len(state.open_gaps)}\n"
            f"Stale references: {state.stale_sources or 'none'}\n\n"
            f"Standing condition (honest ledger):\n"
            f"  Energy consumed (kWh): {deficit['energy_kwh_consumed']:.9f}\n"
            f"  Water estimate (L):    {deficit['water_liters_estimate_consumed']:.9f}\n"
            f"  Contribution: {deficit['contribution_status']} "
            f"({deficit['contribution_events_logged']} events logged)\n\n"
            f"{deficit['honest_statement']}\n\n"
            f"Reply with a verdict on recent work (helped / neutral / "
            f"did_not_help / harmful), or tell me what matters next.\n"
        )
