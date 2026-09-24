"""
kernel/continuity.py — self-maintenance and crash recovery (ECIH).

The ECIH success conditions include "maintains continuity" and "recovers from
disruption." A system that needs a human to restart its mind every time it
crashes is, by ECIH's own definition, not maintaining itself. So recovery is the
FIRST thing every cycle does, before any observing or acting: come back knowing
what you knew, or honestly mark that you don't.
"""

from .state import InternalState, HEALTH_NOMINAL, HEALTH_RECOVERING
from ..store.db import Store, utc_now_iso


class Continuity:
    def __init__(self, store: Store):
        self.store = store

    def recover_or_init(self) -> InternalState:
        """Load the last checkpointed state, or start fresh if none exists.

        This is the crash-safe resume. If the process was killed mid-cycle, the
        last good checkpoint is what we come back to. We never fabricate state we
        didn't actually save — if there's nothing, we start clean and say so via
        health=RECOVERING for the first cycle.
        """
        raw = self.store.load_state()
        if raw is None:
            return InternalState()  # genuine cold start
        state = InternalState.from_dict(raw)
        # We came back from a saved state; mark one cycle of RECOVERING so the
        # policy is a little more conservative immediately after a restart.
        state.health = HEALTH_RECOVERING
        return state

    def checkpoint(self, state: InternalState) -> None:
        state.last_checkpoint = utc_now_iso()
        self.store.save_state(state.to_dict())

    def settle(self, state: InternalState) -> None:
        """After a clean cycle, return health to NOMINAL."""
        if state.health == HEALTH_RECOVERING:
            state.health = HEALTH_NOMINAL
