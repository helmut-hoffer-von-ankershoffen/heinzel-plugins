// This small view needs no bundler. A specialist view can use the same versioned SDK with its own build.
// Pane structure: the content only. It has no actions, so there is no divider and no bottom action row.
export default function createView(sdk) {
  if (sdk.abi !== 1) throw new Error("Example requires plugin SDK 1");
  return function Inspector({data, loading}) {
    return sdk.React.createElement("section", {"aria-label": "Example", className: "p-4"},
      sdk.React.createElement("h2", null, "Example"),
      sdk.React.createElement("p", {role: "status", className: "text-6xl font-semibold"}, loading ? "Loading…" : String(data)));
  };
}
