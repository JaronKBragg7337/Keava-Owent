"""
membrane/approval.py — the human-in-the-loop gate.

Actions the membrane flags (LOCK-mode, destructive, high-impact) are queued here
and BLOCK until a human decides. The system does not proceed on its own. The
queue lives in the durable store so a pending approval survives a restart — the
human's authority is not lost when the process bounces.
"""

import uuid
from ..store.db import Store


class ApprovalQueue:
    def __init__(self, store: Store):
        self.store = store

    def request(self, cycle_id: int, action: dict) -> str:
        approval_id = str(uuid.uuid4())
        self.store.enqueue_approval(approval_id, cycle_id, action)
        return approval_id

    def pending(self) -> list:
        return self.store.pending_approvals()

    def approve(self, approval_id: str) -> None:
        self.store.decide_approval(approval_id, True)

    def deny(self, approval_id: str) -> None:
        self.store.decide_approval(approval_id, False)
