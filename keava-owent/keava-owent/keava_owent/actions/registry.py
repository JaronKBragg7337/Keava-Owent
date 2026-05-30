"""
actions/registry.py — the declared capabilities the system may use.

This is the explicit list of what the system can DO. Nothing the system attempts
is valid unless it is a registered capability AND passes the membrane. Keeping
capabilities explicit and small is the same principle as the membrane: the
surface of reach is auditable, not open-ended.

The v1 skeleton ships a deliberately tiny capability set, all low-reach:
  - observe:        look at something (always EXPLORE-safe)
  - relate_memory:  assert a relationship in the memory graph
  - draft_note:     write a non-canonical working file (DRAFT)
  - report_to_operator: send the honest ledger to the operator via transport
"""

ALLOWED_KINDS = {
    "observe",
    "relate_memory",
    "draft_note",
    "report_to_operator",
    "restore_reference",
    "relate_knowledge",
    "report_and_ask",
    # High-impact / gated kinds are declared so the membrane can recognize them,
    # but they require approval (and, for email_other_person, explicit enabling):
    "overwrite_canonical",
    "delete_file",
    "email_other_person",
}


def is_registered(kind: str) -> bool:
    return kind in ALLOWED_KINDS
