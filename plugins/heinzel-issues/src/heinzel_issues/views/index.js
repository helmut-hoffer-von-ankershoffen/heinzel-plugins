// Issues: what you reported or requested, in three plain states. No bundler: React comes from the plugin SDK.
// Everything happens in the app: setting it up, sending (with an optional file), and opening a report to read what
// was sent and what happened since. Forms go through the view's declared actions (`submit(action, values)`): the app
// shows the call and asks before it runs, and rejects when the person cancels.
const MARKS = { received: "○", working: "◐", done: "✓" };
export const MAX_FILE_BYTES = 2 * 1024 * 1024;
const KINDS = "image/png,image/jpeg,text/plain,.png,.jpg,.jpeg,.txt,.log,.md";

export function statusLine(report) {
  return `${MARKS[report.state] ?? "○"} ${report.status}`;
}

/** What was sent beyond the title: the title is the first line of the text, so it is not shown twice. */
export function rest(report) {
  const body = (report.body || "").trim();
  const title = (report.title || "").trim();
  return body.startsWith(title) ? body.slice(title.length).trim() : body;
}

/** Everything that is stored with a report besides what the person typed, said before they send. */
export function sentAs(sender, labels) {
  const tags = (labels || []).join(", ");
  return `Sent to the tracker under your login name ${sender}${tags ? `, with the labels ${tags}` : ""}.`;
}

/** `7 Nov 2026`, or nothing while the moment is not known. */
export function day(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

/** A chosen file as the `send` action takes it: its name and base64 content. Refuses one over 2 MiB. */
export async function encodeFile(file) {
  if (file.size > MAX_FILE_BYTES) throw new Error(`${file.name} is larger than 2 MiB.`);
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let start = 0; start < bytes.length; start += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(start, start + 0x8000));
  }
  return { file_name: file.name, file_data: btoa(binary) };
}

/** Whether this Heinzel shows a long form value shortened in its confirmation, so a file can be sent from here. */
export function takesFiles(sdk) {
  return Array.isArray(sdk.features) && sdk.features.includes("form-long-values");
}

export default function createView(sdk) {
  if (sdk.abi !== 1) throw new Error("Issues requires Heinzel plugin SDK 1");
  const h = sdk.React.createElement;
  const { useState, useId } = sdk.React;
  const idle = { busy: false, message: null, failed: false };

  function Message({ state }) {
    if (!state.message) return null;
    return h("p", { role: state.failed ? "alert" : "status", className: state.failed ? "hzi-bad" : "hzi-muted" }, state.message);
  }

  function Setup({ submit, problem, folder, labels }) {
    const id = useId();
    const [values, setValues] = useState({ path: folder || "", labels: (labels || []).join(", "), releases: "" });
    const [state, setState] = useState(idle);
    const field = (name, label, hint, required) => h("div", { className: "hzi-field" },
      h("label", { htmlFor: `${id}-${name}`, className: "hzi-label" }, label),
      h("input", {
        id: `${id}-${name}`, className: "hzi-input", type: "text", value: values[name], required,
        autoComplete: "off", spellCheck: false, "aria-describedby": `${id}-${name}-hint`,
        onChange: (event) => setValues({ ...values, [name]: event.target.value }),
      }),
      h("p", { id: `${id}-${name}-hint`, className: "hzi-muted hzi-hint" }, hint),
    );
    const connect = async (event) => {
      event.preventDefault();
      if (!values.path.trim()) return;
      setState({ busy: true, message: "Checking the folder…", failed: false });
      // Labels always go along: what the field says is the whole list, so emptying it clears them.
      const sent = { path: values.path.trim(), labels: values.labels.trim() };
      if (values.releases.trim()) sent.releases = values.releases.trim();
      try {
        await submit("connect", sent);
        setState({ busy: false, message: "Issue tracking is set up.", failed: false });
      } catch (error) {
        setState({ busy: false, message: error?.message || "Not set up; nothing was saved.", failed: true });
      }
    };
    return h("form", { className: "hzi-form", onSubmit: connect, "aria-label": "Set up issue tracking" },
      h("p", { role: "status" }, problem || "Issue tracking is not set up."),
      field("path", "Tracker folder", "The folder on this computer that holds the Beads database, e.g. ~/Code/team-board.", true),
      h("details", { className: "hzi-more" },
        h("summary", null, "More options"),
        field("labels", "More labels", "Labels every new report also gets, separated by commas. Leave empty for none.", false),
        field("releases", "Release clones", "Git clones whose tags are releases, separated by commas, to show which release shipped a report.", false),
      ),
      h(Message, { state }),
      h("div", { className: "hzi-actions" },
        h(sdk.Button, { type: "submit", variant: "default", disabled: state.busy || !values.path.trim() }, state.busy ? "Checking…" : "Set up issue tracking"),
      ),
    );
  }

  function Composer({ submit, sender, labels }) {
    const id = useId();
    const [text, setText] = useState("");
    const [file, setFile] = useState(null);
    const [state, setState] = useState(idle);
    const send = async (event) => {
      event.preventDefault();
      if (!text.trim()) return;
      setState({ busy: true, message: "Sending…", failed: false });
      try {
        await submit("send", file ? { text, ...(await encodeFile(file)) } : { text });
        setText("");
        setFile(null);
        setState({ busy: false, message: "Received. You will see here when someone is on it.", failed: false });
      } catch (error) {
        // Cancelling the confirmation rejects too; the text stays, so nothing typed is lost.
        setState({ busy: false, message: error?.message || "Not sent; your text is still here.", failed: true });
      }
    };
    return h("form", { className: "hzi-form", onSubmit: send, "aria-labelledby": `${id}-label` },
      h("label", { id: `${id}-label`, htmlFor: `${id}-text`, className: "hzi-label" }, "Report or request"),
      h("textarea", {
        id: `${id}-text`, className: "hzi-text", rows: 3, maxLength: 20000, value: text, required: true,
        placeholder: "What happened, or what would you like?", onChange: (event) => setText(event.target.value),
      }),
      takesFiles(sdk) && h("div", { className: "hzi-field" },
        h("label", { htmlFor: `${id}-file`, className: "hzi-label" }, "Screenshot or file (optional)"),
        h("input", {
          // A new key empties the chooser after a send; a file input's value cannot be set.
          key: file ? "chosen" : "empty", id: `${id}-file`, className: "hzi-file", type: "file", accept: KINDS,
          "aria-describedby": `${id}-file-hint`, onChange: (event) => setFile(event.target.files?.[0] ?? null),
        }),
        h("p", { id: `${id}-file-hint`, className: "hzi-muted hzi-hint" }, file ? `${file.name} will be sent with it.` : "A PNG or JPEG image or a text file, up to 2 MiB."),
      ),
      sender && h("p", { className: "hzi-muted hzi-hint" }, sentAs(sender, labels)),
      h(Message, { state }),
      h("div", { className: "hzi-actions" },
        h(sdk.Button, { type: "submit", disabled: state.busy || !text.trim() }, state.busy ? "Sending…" : "Send"),
      ),
    );
  }

  function Item({ report }) {
    const id = useId();
    const [open, setOpen] = useState(false);
    const history = report.history || [];
    const files = report.attachments || [];
    return h("li", { className: "hzi-item" },
      h("button", {
        type: "button", className: "hzi-row", "aria-expanded": open, "aria-controls": `${id}-detail`,
        onClick: () => setOpen(!open),
      },
        h("span", { className: "hzi-title" }, report.title),
        h("span", { className: `hzi-state hzi-${report.state}` }, statusLine(report)),
      ),
      open && h("div", { id: `${id}-detail`, className: "hzi-detail" },
        rest(report) && h("p", { className: "hzi-body" }, rest(report)),
        files.length > 0 && h("p", { className: "hzi-muted" }, `Sent with: ${files.join(", ")}`),
        h("ol", { className: "hzi-history", "aria-label": "History" }, history.map((step) =>
          h("li", { key: step.label },
            h("span", null, step.label),
            h("span", { className: "hzi-muted" }, day(step.at)),
          ),
        )),
      ),
    );
  }

  return function Issues({ data, loading, submit }) {
    if (loading && !data) return h("section", { "aria-label": "Issues", className: "hzi" },
      h("p", { role: "status", className: "hzi-muted" }, "Loading…"));
    if (!data) return h("section", { "aria-label": "Issues", className: "hzi" },
      h("p", { role: "status" }, "Issues cannot be shown here."));
    if (!data.ready) {
      return h("section", { "aria-label": "Issues", className: "hzi" },
        h(Setup, { submit, problem: data.problem, folder: data.folder, labels: data.extra_labels }),
      );
    }
    const reports = data.reports || [];
    return h("section", { "aria-label": "Issues", className: "hzi" },
      reports.length
        ? h("ul", { className: "hzi-list", "aria-label": "Your reports and requests" }, reports.map((report) => h(Item, { key: report.details?.id ?? report.title, report })))
        : h("p", { role: "status", className: "hzi-muted" }, "Nothing reported yet."),
      h(Composer, { submit, sender: data.sender, labels: data.labels }),
    );
  };
}
