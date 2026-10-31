"""Show the real theme on a representative local contract, using only fictional demonstration content."""

import os
import runpy
import sys
from pathlib import Path

CONTRACT = """---
name: launch-review
kind: responsibility
version: 1.0.0
description: Keep the launch plan, owners and readiness checks clear.
hz:
  schema: 1
  title: Launch review
  inputs: {}
  outputs:
    review: {format: markdown}
  agent:
    tools: [Read]
    max_usd: 0.5
  timeout: 10m
---

# Launch review

### Goal

The launch review is ready, with clear owners and three useful readiness checks.

### Requires

No external inputs in this isolated appearance demonstration.

### Maintains

- `review`: a concise launch review with owners, readiness checks and the next milestone.

### Done when

- [ ] Mira has verified the export boundary.
- [ ] Jonas has checked the API notes.
- [ ] Priya has reviewed the phone screenshots.

This is local demonstration content for the applied theme. No report has been generated.
"""
folder = Path(os.environ["HZ_STATE_DIR"]) / "demonstration-contracts"
folder.mkdir(parents=True, exist_ok=True)
(folder / "launch-review.prose.md").write_text(CONTRACT)
os.environ["HZ_HEINZEL__USER_DIR"] = str(folder)
sys.argv = ["hz", *sys.argv[1:]]
runpy.run_module("heinzel", run_name="__main__")
