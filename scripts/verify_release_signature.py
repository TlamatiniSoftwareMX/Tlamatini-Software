#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"


def main() -> int:
    secret = os.environ.get("TLAMATINI_RELEASE_SIGNING_KEY", "").strip()
    if not secret:
        print("ERROR: define TLAMATINI_RELEASE_SIGNING_KEY para verificar firma.")
        return 1

    checksums_path = DIST_DIR / "SHA256SUMS.json"
    signature_path = DIST_DIR / "SHA256SUMS.sig.json"
    if not checksums_path.exists() or not signature_path.exists():
        print("ERROR: faltan SHA256SUMS.json o SHA256SUMS.sig.json")
        return 1

    payload = json.loads(checksums_path.read_text(encoding="utf-8"))
    signature_data = json.loads(signature_path.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), encoded, hashlib.sha256).digest()
    actual = base64.b64decode(signature_data["signature"].encode("ascii"))
    if not hmac.compare_digest(expected, actual):
        print("ERROR: firma inválida")
        return 1

    print("Firma OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
