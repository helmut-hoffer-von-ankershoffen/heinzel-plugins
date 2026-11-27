"""The screenshot definition: the checked-in, hand-edited `docs/screenshot-definition.json` of each plugin.

It is the whole plan (scenes, captions, optional fixture bootstrap and browser clock). Capture reads it and never
plans: no agent writes or approves it. Edit it like any other file and review it in the pull request.
"""

import json
from pathlib import Path

from heinzel_plugin_tools.privacy import CaptureError, atomic_text, safe_path

DEFINITION = Path("docs/screenshot-definition.json")
MAX_DEFINITION = 64 * 1024


def definition_text(plan: dict) -> str:
    """The canonical file text of a definition: stable key order, two-space indent, one final newline."""
    return json.dumps(plan, indent=2, ensure_ascii=False) + "\n"


def load_definition(root: Path) -> dict | None:
    """The parsed definition, or None when the plugin has none yet."""
    path = safe_path(root, DEFINITION)
    if not path.exists():
        return None
    text = path.read_text()
    if len(text.encode()) > MAX_DEFINITION:
        raise CaptureError(f"{DEFINITION} is larger than 64 KiB; keep the definition to its scenes")
    try:
        data = json.loads(text)
    except ValueError as error:
        raise CaptureError(f"{DEFINITION} is not valid JSON (line {getattr(error, 'lineno', '?')})") from None
    return data


def write_definition(root: Path, plan: dict) -> None:
    """Write a definition in its canonical form."""
    path = safe_path(root, DEFINITION)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_text(path, definition_text(plan))
