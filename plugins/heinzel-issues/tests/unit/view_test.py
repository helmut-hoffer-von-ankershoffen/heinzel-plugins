"""The app view's form sends the typed text through the `send` action, and falls back on an older Heinzel."""

import json
from pathlib import Path

import pytest
from nodejs_wheel import node

pytestmark = pytest.mark.unit
VIEW = Path(__file__).resolve().parents[2] / "src" / "heinzel_issues" / "views" / "index.js"

# A React stand-in: elements are plain objects, `useState` hands out preset values and records what is set.
HARNESS = """
import createView from %(view)s;
const preset = [], set = [], calls = [];
const React = {
  createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
  useId: () => "v",
  useState: (initial) => [preset.length ? preset.shift() : initial, (value) => set.push(value)],
};
const find = (node, test) => {
  if (!node || typeof node !== "object") return null;
  if (test(node)) return node;
  for (const child of node.children || []) { const hit = find(child, test); if (hit) return hit; }
  return null;
};
const Issues = createView({ abi: 1, React, Button: "button" });
const composer = (submit) => {
  const tree = Issues({ data: { ready: true, reports: [] }, submit, run: (key) => calls.push(["run", key]) });
  const element = find(tree, (node) => typeof node.type === "function");
  return element.type(element.props);
};
const scenario = %(scenario)s;
if (scenario === "fallback") {
  find(composer(undefined), (node) => node.type === "button").props.onClick();
} else {
  preset.push("Dark mode loses the focus ring", { busy: false, message: null, failed: false });
  const form = composer(async (action, values) => {
    calls.push(["submit", action, values]);
    if (scenario === "cancel") throw new Error("Cancelled");
  });
  await form.props.onSubmit({ preventDefault() {} });
}
console.log(JSON.stringify({ calls, set }));
"""


def render(tmp_path: Path, scenario: str) -> dict:
    script = tmp_path / "harness.mjs"
    script.write_text(HARNESS % {"view": json.dumps(VIEW.as_uri()), "scenario": json.dumps(scenario)})
    # The Node.js that pyright[nodejs] brings into every test environment, so this never depends on the machine.
    done = node([str(script)], return_completed_process=True, capture_output=True, text=True, timeout=30, check=True)
    return json.loads(done.stdout)


def test_the_form_sends_the_text_through_the_send_action(tmp_path):
    result = render(tmp_path, "send")
    assert result["calls"] == [["submit", "send", {"text": "Dark mode loses the focus ring"}]]
    assert "" in result["set"]  # the text is cleared
    assert result["set"][-1]["failed"] is False
    assert result["set"][-1]["message"].startswith("Received.")


def test_a_cancelled_or_failed_send_keeps_the_text_and_says_so(tmp_path):
    result = render(tmp_path, "cancel")
    assert result["calls"] == [["submit", "send", {"text": "Dark mode loses the focus ring"}]]
    assert "" not in result["set"]
    assert result["set"][-1] == {"busy": False, "message": "Cancelled", "failed": True}


def test_an_older_heinzel_without_submit_opens_the_terminal_command(tmp_path):
    assert render(tmp_path, "fallback")["calls"] == [["run", "report"]]
