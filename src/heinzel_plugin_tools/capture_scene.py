"""Run one capture CLI scene using a private argument request separate from stdin."""

import json
import os
import runpy
import sys
import unicodedata
from pathlib import Path

REQUEST_FD = "HZ_CAPTURE_SCENE_REQUEST_FD"
ENTRYPOINT = "HZ_CAPTURE_SCENE_ENTRYPOINT"
REQUEST_LIMIT = 1024 * 1024


def valid_command(command: object) -> bool:
    """Bound command arguments without interpreting shell syntax."""
    return (
        isinstance(command, list)
        and 0 < len(command) <= 40
        and all(
            isinstance(arg, str) and len(arg) <= 2000 and not any(unicodedata.category(c) in {"Cc", "Cf"} for c in arg)
            for arg in command
        )
    )


def main() -> None:
    try:
        descriptor = int(os.environ.pop(REQUEST_FD))
        entrypoint = Path(os.environ.pop(ENTRYPOINT))
        if descriptor < 3 or not entrypoint.is_absolute() or not entrypoint.is_file():
            raise ValueError
        with os.fdopen(descriptor, "rb") as request:
            payload = request.read(REQUEST_LIMIT + 1)
        if len(payload) > REQUEST_LIMIT:
            raise ValueError
        args = json.loads(payload)
        if not valid_command(args):
            raise ValueError
    except (KeyError, OSError, RecursionError, ValueError):
        raise SystemExit("Invalid capture CLI scene request") from None

    arguments = args[1:] if args[:1] == ["hz"] else args
    sys.argv[:] = [str(entrypoint), *arguments]
    runpy.run_path(str(entrypoint), run_name="__main__")


if __name__ == "__main__":
    main()
