// This small view needs no bundler. A specialist view can use the same versioned SDK with its own build.
export default function createView(sdk) {
  if (sdk.abi !== 1) throw new Error("Example requires plugin SDK 1");
  return function Inspector({data, loading, onClose}) {
    return sdk.React.createElement("section", {"aria-label": "Example", className: "p-4"},
      sdk.React.createElement("h2", null, "Example"),
      sdk.React.createElement("p", {role: "status"}, loading ? "Loading…" : `The value is ${data}.`),
      sdk.React.createElement(sdk.Button, {onClick: onClose}, "Close example"));
  };
}
