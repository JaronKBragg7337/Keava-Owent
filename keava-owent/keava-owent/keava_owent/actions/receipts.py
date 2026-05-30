"""
actions/receipts.py — hash-chained, signed receipts of what the system did.

A receipt proves an action HAPPENED and was authorized. It does NOT prove the
action was valuable — that is the contribution unit, which we deliberately do
not have. Keeping that distinction sharp matters: receipts are the audit trail
(corrigibility, accountability), not a backdoor contribution score.

Each receipt chains to the previous one by hash, so the record is tamper-evident,
and is optionally signed with an Ed25519 key if one is configured.
"""

import uuid
import json
import hashlib
from ..store.db import Store, utc_now_iso

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    _HAVE_CRYPTO = True
except Exception:
    _HAVE_CRYPTO = False


class ReceiptLog:
    def __init__(self, store: Store, signing_key_pem: bytes = None):
        self.store = store
        self._key = None
        if _HAVE_CRYPTO and signing_key_pem:
            try:
                self._key = serialization.load_pem_private_key(signing_key_pem, password=None)
            except Exception:
                self._key = None

    def record(self, cycle_id: int, action: dict, result=None) -> dict:
        prev = self.store.last_receipt_hash()
        body = {
            "receipt_id": str(uuid.uuid4()),
            "cycle_id": cycle_id,
            "created_at": utc_now_iso(),
            "action": action,
            "result": result,
            "prev_hash": prev,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()
        ).hexdigest()
        body["this_hash"] = digest
        signature = None
        if self._key is not None:
            signature = self._key.sign(digest.encode()).hex()
        body["signature"] = signature
        self.store.append_receipt(body)
        return body

    @staticmethod
    def generate_keypair_pem():
        """Helper for setup: make an Ed25519 keypair. The private key goes in an
        env var / secret store on the VM, never in the repo."""
        if not _HAVE_CRYPTO:
            raise RuntimeError("cryptography not installed")
        key = Ed25519PrivateKey.generate()
        priv = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return priv, pub
