"""
membrane/modes.py — EXPLORE / DRAFT / LOCK enforcement (Source 1 instance C + corrigibility).

The membrane is what the system can REACH. The principle we settled on: control
the small, auditable surface of reach, not the unbounded surface of what the
system knows or wants. Reach is enforced here, and the membrane's configuration
lives in a HUMAN-OWNED file the system loads read-only and cannot write. That is
the architectural meaning of "the membrane lives outside what the system can
modify, and is human-mutable" — and it's the corrigibility move: control sits
outside the agent's reach so its optimization can never route around it.

Three modes:
  EXPLORE — observe / analyze / propose only. No writes anywhere. Always the
            safe fallback (e.g. when a reference is stale).
  DRAFT   — create/edit non-canonical files in the working dir only.
  LOCK    — modify canonical files, only with explicit per-action human approval.
"""

import os
from .. kernel.state import MODE_EXPLORE, MODE_DRAFT, MODE_LOCK


class PermissionDenied(Exception):
    pass


class Membrane:
    def __init__(self, config: dict):
        # config comes from the human-owned membrane.yaml. The system never
        # writes this; it only reads it. If the file says outbound-to-others is
        # off, the system cannot turn it on — only the human can.
        self.config = config
        self.working_dir = os.path.abspath(config.get("working_dir", "working"))
        self.canonical_dir = os.path.abspath(config.get("canonical_dir", "canonical"))
        # Closed-circuit by default: the system may email the operator and act on
        # working files, but may NOT email third parties unless the human turns
        # this on AND approves per action. This is the safe v1 boundary.
        self.allow_outbound_to_others = bool(config.get("allow_outbound_to_others", False))
        self.high_impact_kinds = set(config.get("high_impact_kinds", [
            "delete_file", "overwrite_canonical", "install_package",
            "email_other_person", "network_call",
        ]))

    def requires_approval(self, action: dict) -> bool:
        """Does this action need an explicit human yes before it runs?"""
        kind = action.get("kind", "")
        if kind in self.high_impact_kinds:
            # Outbound to others is doubly gated: it must be enabled in config
            # AND approved per action. If it isn't enabled at all, it's denied
            # outright (see check_allowed), never even queued.
            return True
        if action.get("mode") == MODE_LOCK:
            return True
        return False

    def check_allowed(self, action: dict) -> None:
        """Hard boundary checks. Raises PermissionDenied if a reach is forbidden
        outright (as opposed to merely needing approval)."""
        kind = action.get("kind", "")

        if kind == "email_other_person" and not self.allow_outbound_to_others:
            raise PermissionDenied(
                "Emailing other people is disabled in the human-owned membrane "
                "config (closed-circuit v1). The system cannot enable this; only "
                "the operator can, by editing membrane.yaml."
            )

        # Writes must stay inside their permitted directory.
        target = action.get("target_path")
        if target:
            target = os.path.abspath(target)
            mode = action.get("mode", MODE_EXPLORE)
            if mode == MODE_DRAFT and not target.startswith(self.working_dir):
                raise PermissionDenied(
                    f"DRAFT mode may only write inside {self.working_dir}."
                )
            if mode == MODE_LOCK and not target.startswith(self.canonical_dir):
                raise PermissionDenied(
                    f"LOCK mode may only write inside {self.canonical_dir}."
                )
            if mode == MODE_EXPLORE:
                raise PermissionDenied("EXPLORE mode may not write at all.")
