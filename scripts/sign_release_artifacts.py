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


def _load_checksums() -> dict:
    path = DIST_DIR / "SHA256SUMS.json"
    if not path.exists():
        raise RuntimeError("Falta dist/SHA256SUMS.json")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    secret = os.environ.get("TLAMATINI_RELEASE_SIGNING_KEY", "").strip()
    if not secret:
        print("ERROR: define TLAMATINI_RELEASE_SIGNING_KEY para firmar artefactos.")
        return 1

    payload = _load_checksums()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), encoded, hashlib.sha256).digest()
    output = {
        "algorithm": "HMAC-SHA256",
        "signed_file": "dist/SHA256SUMS.json",
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    path = DIST_DIR / "SHA256SUMS.sig.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Firma generada en {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
