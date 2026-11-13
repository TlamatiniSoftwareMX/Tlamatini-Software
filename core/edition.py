"""Build edition embedded in the executable; no user data is read here."""
import json
import sys
from pathlib import Path


def edition_name() -> str:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    try:
        return str(json.loads((root / "edition.json").read_text(encoding="utf-8")).get("edition", "full"))
    except (OSError, ValueError, TypeError, AttributeError):
        return "full"


def ai_disabled() -> bool:
    return edition_name() == "no-ai"
