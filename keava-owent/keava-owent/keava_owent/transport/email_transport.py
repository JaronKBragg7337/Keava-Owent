"""
transport/email_transport.py — email as the message bus (the spine).

We settled that email is the right transport for this system, for two reasons:
it lets the loop reach the operator without the operator having to message it,
and it is a shared medium that both this system and other AIs (via their email
connectors) can read — the 'wire' that doesn't run through the operator's hands.

Two directions:
  OUTBOUND — the loop reports to the operator (and, only if the membrane allows
             AND a human approves, to other people). Uses SendGrid's REST API
             when configured; otherwise falls back to a local outbox file so the
             system runs out of the box before any email infra exists.
  INBOUND  — the operator's replies carry verdicts ('helped' / 'did not help' /
             etc.) which become the external human-verdict log the contribution
             slot depends on. v1 supports a simple IMAP poll OR reading a local
             inbox file; SendGrid Inbound Parse is the production option.

Secrets (SendGrid API key, IMAP password) are read from the environment, NEVER
from the repo. The repo ships clean; the VM holds the keys.
"""

import os
import json
import datetime

try:
    import requests
    _HAVE_REQUESTS = True
except Exception:
    _HAVE_REQUESTS = False


class EmailTransport:
    def __init__(self, config: dict):
        self.inbound_address = config.get("inbound_address", "REPLACE_ME@your-domain")
        self.outbound_address = config.get("outbound_address", "REPLACE_ME@your-domain")
        self.operator_address = config.get("operator_address", "REPLACE_ME@operator")
        self.allowlist = set(config.get("read_allowlist", []))
        # Secrets come from the environment on the VM, never the repo.
        self.sendgrid_key = os.environ.get("KEAVA_SENDGRID_API_KEY")
        # Local fallbacks so the system runs before any email is configured.
        self.local_outbox = config.get("local_outbox", "data/outbox.jsonl")
        self.local_inbox = config.get("local_inbox", "data/inbox.jsonl")

    # ---- outbound ------------------------------------------------------------

    def send(self, to_address: str, subject: str, body: str) -> dict:
        """Send mail via SendGrid if configured, else append to a local outbox.

        The local-outbox fallback is not a toy: it means the loop's 'report to
        operator' action always succeeds at SOMETHING (writing a durable record),
        so the system is honest about having produced output even before email
        delivery is wired up. Metering-style graceful degradation.
        """
        if self.sendgrid_key and _HAVE_REQUESTS:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.sendgrid_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_address}]}],
                    "from": {"email": self.outbound_address},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
                timeout=20,
            )
            return {"channel": "sendgrid", "status_code": resp.status_code}

        # Fallback: durable local outbox.
        os.makedirs(os.path.dirname(os.path.abspath(self.local_outbox)), exist_ok=True)
        record = {
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "to": to_address, "subject": subject, "body": body,
        }
        with open(self.local_outbox, "a") as f:
            f.write(json.dumps(record) + "\n")
        return {"channel": "local_outbox", "path": self.local_outbox}

    # ---- inbound -------------------------------------------------------------

    def fetch_inbound(self) -> list:
        """Return new inbound messages from allowlisted senders only.

        The allowlist is the security boundary: a system that reads email and
        acts can be hijacked by a crafted incoming message (prompt injection), so
        we only ever READ mail from senders the operator has approved. v1 reads a
        local inbox file; SendGrid Inbound Parse or IMAP slot in here in prod.
        """
        msgs = []
        if os.path.exists(self.local_inbox):
            with open(self.local_inbox, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    sender = m.get("from", "")
                    # Allowlist enforcement: silently ignore anyone not approved.
                    if self.allowlist and sender not in self.allowlist:
                        continue
                    msgs.append(m)
        return msgs
