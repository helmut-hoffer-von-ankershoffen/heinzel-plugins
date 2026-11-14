"""The app view: set up, send (with a file where the app can confirm one), and open a report, with no terminal."""

import json
from pathlib import Path

import pytest
from nodejs_wheel import node

pytestmark = pytest.mark.unit
VIEW = Path(__file__).resolve().parents[2] / "src" / "heinzel_issues" / "views" / "index.js"

# A React stand-in: elements are plain objects, `useState` hands out preset values and records what is set.
HARNESS = """
import createView, { day, encodeFile, statusLine } from %(view)s;
const preset = [], set = [], calls = [];
const React = {
  createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat() }),
  useId: () => "v",
  useState: (initial) => [preset.length ? preset.shift() : initial, (value) => set.push(value)],
};
const expand = (node) => {
  if (!node || typeof node !== "object") return node;
  if (typeof node.type === "function") return expand(node.type(node.props));
  return { ...node, children: (node.children || []).map(expand) };
};
const all = (node, test, found = []) => {
  if (!node || typeof node !== "object") return found;
  if (test(node)) found.push(node);
  for (const child of node.children || []) all(child, test, found);
  return found;
};
const text = (node) => {
  if (typeof node === "string") return node;
  return !node || typeof node !== "object" ? "" : (node.children || []).map(text).join(" ");
};
const scenario = %(scenario)s;
const sdk = { abi: 1, React, Button: "button", features: scenario.features };
const Issues = createView(sdk);
const idle = { busy: false, message: null, failed: false };
const submit = async (action, values) => {
  calls.push([action, values]);
  if (scenario.fail) throw new Error(scenario.fail);
};
const out = {};
if (scenario.name === "send") {
  const file = scenario.file ? new File([scenario.file], "shot.txt", { type: "text/plain" }) : null;
  preset.push("Dark mode loses the focus ring", file, idle);
  const tree = expand(Issues({ data: { ready: true, reports: [] }, submit }));
  out.chooser = all(tree, (node) => node.props.type === "file").length;
  await all(tree, (node) => node.type === "form")[0].props.onSubmit({ preventDefault() {} });
} else if (scenario.name === "setup") {
  preset.push(scenario.values, idle);
  const tree = expand(Issues({ data: { ready: false, problem: scenario.problem, folder: scenario.folder }, submit }));
  out.text = text(tree);
  out.path = all(tree, (node) => node.type === "input")[0].props.value;
  await all(tree, (node) => node.type === "form")[0].props.onSubmit({ preventDefault() {} });
} else if (scenario.name === "open") {
  preset.push(scenario.open);
  const tree = expand(Issues({ data: { ready: true, reports: [scenario.report] }, submit }));
  const row = all(tree, (node) => node.props.className === "hzi-row")[0];
  out.expanded = row.props["aria-expanded"];
  out.text = text(all(tree, (node) => node.type === "li")[0]);
  row.props.onClick();
} else if (scenario.name === "helpers") {
  out.day = [day("2026-11-07T08:33:55Z"), day(null), day("soon")];
  out.line = statusLine({ state: "working", status: "Being worked on" });
  out.encoded = await encodeFile(new File(["hello"], "note.txt"));
  out.large = await encodeFile({ name: "big.png", size: 3 * 1024 * 1024 }).catch((error) => error.message);
  out.old = (() => { try { createView({ abi: 2 }); } catch (error) { return error.message; } })();
  out.loading = text(expand(Issues({ loading: true })));
  out.missing = text(expand(Issues({})));
}
console.log(JSON.stringify({ calls, set: set.map((value) => value instanceof File ? "file" : value), ...out }));
"""
IDLE = {"busy": False, "message": None, "failed": False}


def render(tmp_path: Path, name: str, **scenario: object) -> dict:
    script = tmp_path / "harness.mjs"
    script.write_text(HARNESS % {"view": json.dumps(VIEW.as_uri()), "scenario": json.dumps({"name": name, **scenario})})
    # The Node.js that pyright[nodejs] brings into every test environment, so this never depends on the machine.
    done = node([str(script)], return_completed_process=True, capture_output=True, text=True, timeout=30, check=True)
    return json.loads(done.stdout)


def test_the_form_sends_the_text_through_the_send_action(tmp_path):
    result = render(tmp_path, "send")
    assert result["calls"] == [["send", {"text": "Dark mode loses the focus ring"}]]
    assert "" in result["set"]  # the text is cleared
    assert result["set"][-1]["failed"] is False
    assert result["set"][-1]["message"].startswith("Received.")


def test_a_chosen_file_goes_with_the_text_as_name_and_base64(tmp_path):
    result = render(tmp_path, "send", file="hello", features=["form-long-values"])
    assert result["chooser"] == 1
    sent = {"text": "Dark mode loses the focus ring", "file_name": "shot.txt", "file_data": "aGVsbG8="}
    assert result["calls"] == [["send", sent]]
    assert None in result["set"]  # the chosen file is cleared with the text


def test_a_heinzel_that_cannot_confirm_a_file_offers_no_chooser(tmp_path):
    assert render(tmp_path, "send")["chooser"] == 0
    assert render(tmp_path, "send", features=["something-else"])["chooser"] == 0


def test_a_cancelled_or_failed_send_keeps_the_text_and_says_so(tmp_path):
    result = render(tmp_path, "send", fail="Cancelled")
    assert result["calls"] == [["send", {"text": "Dark mode loses the focus ring"}]]
    assert "" not in result["set"]
    assert result["set"][-1] == {"busy": False, "message": "Cancelled", "failed": True}


def test_setup_is_a_form_in_the_app_and_sends_only_what_was_filled_in(tmp_path):
    values = {"path": " ~/Code/team-board ", "labels": "", "releases": ""}
    result = render(tmp_path, "setup", values=values, folder="~/old")
    assert "Issue tracking is not set up." in result["text"]
    assert "hz " not in result["text"]  # no terminal command anywhere
    assert result["calls"] == [["connect", {"path": "~/Code/team-board"}]]
    assert result["set"][-1] == {"busy": False, "message": "Issue tracking is set up.", "failed": False}

    values = {"path": "/board", "labels": "intake", "releases": "/harbor, /pier"}
    result = render(tmp_path, "setup", values=values, problem="The tracker refused: locked", fail="No database there")
    assert "The tracker refused: locked" in result["text"]
    assert result["calls"] == [["connect", {"path": "/board", "labels": "intake", "releases": "/harbor, /pier"}]]
    assert result["set"][-1] == {"busy": False, "message": "No database there", "failed": True}


def test_setup_without_a_folder_sends_nothing(tmp_path):
    result = render(tmp_path, "setup", values={"path": "  ", "labels": "", "releases": ""})
    assert result["calls"] == []
    assert result["set"] == []


REPORT = {
    "title": "The footer clock jumps",
    "body": "The footer clock jumps\nIt moves by a pixel.",
    "state": "done",
    "status": "Released in 0.9.27 on 7 Nov 2026",
    "attachments": ["shot.png"],
    "history": [
        {"label": "Sent", "at": "2026-11-05T09:00:00Z"},
        {"label": "Being worked on", "at": None},
        {"label": "Done", "at": "2026-11-06T10:00:00Z"},
        {"label": "Released in 0.9.27", "at": "2026-11-07T00:00:00Z"},
    ],
    "details": {"id": "demo-1"},
}


def test_a_report_opens_to_what_was_sent_and_its_history(tmp_path):
    closed = render(tmp_path, "open", report=REPORT, open=False)
    assert closed["expanded"] is False
    assert "It moves by a pixel." not in closed["text"]
    assert closed["set"] == [True]  # a click opens it

    opened = render(tmp_path, "open", report=REPORT, open=True)
    assert opened["expanded"] is True
    for words in ("It moves by a pixel.", "Sent with: shot.png", "Sent", "5 Nov 2026", "Being worked on", "Done"):
        assert words in opened["text"]
    assert "Released in 0.9.27" in opened["text"]
    assert opened["text"].count("The footer clock jumps") == 1  # the title is not repeated in what was sent
    assert "demo-1" not in opened["text"]  # the tracker's id stays behind the view
    assert opened["set"] == [False]


def test_dates_marks_files_and_the_states_without_data(tmp_path):
    result = render(tmp_path, "helpers")
    assert result["day"] == ["7 Nov 2026", "", ""]
    assert result["line"] == "◐ Being worked on"
    assert result["encoded"] == {"file_name": "note.txt", "file_data": "aGVsbG8="}
    assert result["large"] == "big.png is larger than 2 MiB."
    assert result["old"] == "Issues requires Heinzel plugin SDK 1"
    assert result["loading"] == "Loading…"
    assert result["missing"] == "Issues cannot be shown here."
