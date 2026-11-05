// Failure evidence for the actual FooterPart -> FooterItem -> ContributionToggle path.
// No layout reads during input: geometry and computed visibility are read only after failure.
export function installDiagnostics() {
  const entries = [];
  let previous = "";
  let generation = 0;
  const nodes = new WeakMap();
  const nodeId = (node) => {
    if (!node) return 0;
    if (!nodes.has(node)) nodes.set(node, ++generation);
    return nodes.get(node);
  };
  const region = () => document.querySelector('section[aria-label="Tailscale"]');
  const trigger = () => document.querySelector('[data-footer-content="tailscale:sharing"] button');
  const controls = () => {
    const panel = region();
    return {
      trigger: trigger(),
      switch: panel?.querySelector('[role="switch"]'),
      share: [...(panel?.querySelectorAll("button") ?? [])].find((item) => item.textContent.trim() === "Share"),
      copy: [...(panel?.querySelectorAll("button") ?? [])].find((item) => item.textContent.trim() === "Copy URL"),
      more: document.querySelector('button[aria-label="More status items"]'),
      region: panel,
      overflow: document.querySelector('section[aria-label="More status items"]'),
      anchor: document.querySelector('[data-footer-part="tailscale:sharing"]'),
      host: document.querySelector('[data-footer-host="tailscale:sharing"]'),
    };
  };
  const identity = (target, known) =>
    target === document.body ? "body" : target === document.documentElement ? "document" : Object.entries(known).find(([, item]) => item && (item === target || item.contains(target)))?.[0] ?? "other";
  const sample = (event = "mutation", key = "none", target = null, related = null) => {
    const known = controls();
    const anchor = document.querySelector('[data-footer-part="tailscale:sharing"]');
    const state = {
      event,
      key,
      target: identity(target, known),
      related: identity(related, known),
      focus: identity(document.activeElement, known),
      width: innerWidth,
      height: innerHeight,
      region: !!known.region?.isConnected,
      regionGeneration: nodeId(known.region),
      triggerGeneration: nodeId(known.trigger),
      shareGeneration: nodeId(known.share),
      trigger: !!known.trigger?.isConnected,
      share: !!known.share?.isConnected,
      copy: !!known.copy?.isConnected,
      expanded: known.trigger?.getAttribute("aria-expanded") === "true",
      concealed: anchor?.hasAttribute("inert") === true || anchor?.getAttribute("aria-hidden") === "true",
      overflow: !!known.overflow?.isConnected,
      inOverflow: !!known.overflow?.contains(known.trigger),
      bodyPortal: !!known.region && known.region.parentElement?.parentElement === document.body,
    };
    const signature = JSON.stringify(state);
    if (event === "mutation" && signature === previous) return;
    previous = signature;
    entries.push({ at: Math.round(performance.now()), ...state });
    if (entries.length > 96) entries.shift();
  };
  for (const event of ["focusin", "focusout", "mousedown", "click", "keydown", "keypress", "keyup"])
    document.addEventListener(event, (input) => sample(event, ["Enter", "Tab", "Escape"].includes(input.key) ? input.key : "other", input.target, input.relatedTarget), true);
  new MutationObserver(() => sample()).observe(document, {
    subtree: true, childList: true, attributes: true,
    attributeFilter: ["aria-hidden", "aria-expanded", "inert", "data-footer-hidden"],
  });
  window.__tailscaleDiagnostics = () => {
    sample("failure");
    const known = controls();
    const geometry = Object.fromEntries(Object.entries(known).map(([name, item]) => {
      if (!item) return [name, null];
      const rect = item.getBoundingClientRect();
      const style = getComputedStyle(item);
      return [name, {
        connected: item.isConnected,
        x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height),
        displayed: style.display !== "none", visible: style.visibility === "visible",
        clientRects: item.getClientRects().length > 0,
      }];
    }));
    return { owner: "FooterPart/FooterItem/ContributionToggle", entries, geometry };
  };
}
