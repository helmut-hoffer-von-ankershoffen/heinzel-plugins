// Issues: what you reported or requested, in three plain states. No bundler: React comes from the plugin SDK.
// The form sends what the person typed through the view's `send` action (`submit(action, values)`, Heinzel 0.9.30+):
// the app shows the call and asks before it runs, and rejects when the person cancels. An older Heinzel without
// `submit` gets one button that opens `hz issues submit` in the app terminal instead.
const MARKS = { received: "○", working: "◐", done: "✓" };

export function statusLine(report) {
  return `${MARKS[report.state] ?? "○"} ${report.status}`;
}

export default function createView(sdk) {
  if (sdk.abi !== 1) throw new Error("Issues requires Heinzel plugin SDK 1");
  const h = sdk.React.createElement;
  const { useState, useId } = sdk.React;

  function Composer({ submit, run }) {
    const id = useId();
    const [text, setText] = useState("");
    const [state, setState] = useState({ busy: false, message: null, failed: false });
    if (typeof submit !== "function") {
      return h("div", { className: "hzi-actions" },
        h(sdk.Button, { variant: "default", onClick: () => run?.("report") }, "Report or request"),
      );
    }
    const send = async (event) => {
      event.preventDefault();
      if (!text.trim()) return;
      setState({ busy: true, message: "Sending…", failed: false });
      try {
        await submit("send", { text });
        setText("");
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
      state.message && h("p", { role: state.failed ? "alert" : "status", className: state.failed ? "hzi-bad" : "hzi-muted" }, state.message),
      h("div", { className: "hzi-actions" },
        h(sdk.Button, { type: "submit", disabled: state.busy || !text.trim() }, state.busy ? "Sending…" : "Send"),
      ),
    );
  }

  function Item({ report }) {
    return h("li", { className: "hzi-item" },
      h("span", { className: "hzi-title" }, report.title),
      h("span", { className: `hzi-state hzi-${report.state}` }, statusLine(report)),
    );
  }

  return function Issues({ data, loading, submit, run }) {
    if (loading && !data) return h("p", { role: "status", className: "hzi-muted" }, "Loading…");
    if (!data) return h("p", { role: "status" }, "Issues cannot be shown here; run hz issues list.");
    if (!data.ready) {
      return h("section", { "aria-label": "Issues", className: "hzi" },
        h("p", { role: "status" }, data.problem || "Issue tracking is not set up."),
        h("div", { className: "hzi-actions" },
          h(sdk.Button, { variant: "default", onClick: () => run?.("setup") }, "Set up issue tracking"),
        ),
      );
    }
    const reports = data.reports || [];
    return h("section", { "aria-label": "Issues", className: "hzi" },
      reports.length
        ? h("ul", { className: "hzi-list", "aria-label": "Your reports and requests" }, reports.map((report) => h(Item, { key: report.details?.id ?? report.title, report })))
        : h("p", { role: "status", className: "hzi-muted" }, "Nothing reported yet."),
      h(Composer, { submit, run }),
    );
  };
}
