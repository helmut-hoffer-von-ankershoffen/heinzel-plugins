export default function createView(sdk) {
  if (sdk.abi !== 1) throw new Error("Google source review requires plugin SDK 1");
  const h = sdk.React.createElement;
  return function SourceReview({data, loading}) {
    return h("section", {"aria-label": "Google source review", className: "p-4"},
      h("h2", null, "Google source review"),
      loading ? h("p", {role: "status"}, "Loading source review…") : data?.configured
        ? h(sdk.React.Fragment, null,
          h("p", {className: "break-all"}, `Selected command: ${data.command}`),
          h("p", {className: "break-all"}, `Native executable: ${data.binary}`),
          h("p", {className: "break-all"}, `SHA-256: ${data.binary_sha256}`),
          h("p", null, data.wrapper ? "Supported npm launcher." : "Direct native executable."))
        : h("p", null, "Set the absolute Google Workspace CLI path in your Google settings to review it."),
      h("p", null, "The digest checks byte continuity; it does not authenticate the publisher. This review does not access your Google account or grant a read."));
  };
}
