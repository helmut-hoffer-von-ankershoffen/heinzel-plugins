import assert from "node:assert/strict";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import { installDiagnostics } from "./diagnostics.mjs";

test("captures owner removal, viewport and keyboard focus without copying arbitrary document data", () => {
  const handlers = new Map();
  let observer;
  let layoutReads = 0;
  const secret = "#token=NEVER_COPY_THIS_SESSION";
  const item = (textContent = secret) => ({
    textContent, isConnected: true,
    contains(target) { return target === this; },
    getAttribute() { return secret; },
    hasAttribute() { return false; },
    getBoundingClientRect() { layoutReads++; return { x: 1, y: 2, width: 3, height: 4 }; },
    getClientRects() { return [1]; },
  });
  let share = item("Share");
  const copy = item("Copy URL"), toggle = item(), trigger = item();
  const panel = item();
  panel.querySelector = () => toggle;
  panel.querySelectorAll = () => [share, copy, item(secret)];
  panel.contains = (target) => [share, copy, toggle].includes(target) || target === panel;
  let present = true;
  const document = {
    activeElement: share,
    querySelector(selector) {
      if (selector === 'section[aria-label="Tailscale"]') return present ? panel : null;
      if (selector === '[data-footer-content="tailscale:sharing"] button') return trigger;
      return null;
    },
    addEventListener(type, handler) { handlers.set(type, handler); },
  };
  document.body = item();
  document.documentElement = item();
  const window = {};
  runInNewContext(`(${installDiagnostics.toString()})()`, {
    document, window, innerWidth: 390, innerHeight: 844,
    performance: { now: () => 42 },
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    MutationObserver: class { constructor(callback) { observer = callback; } observe() {} },
  });
  handlers.get("keydown")({ key: "Enter", target: share });
  observer();
  observer(); // Identical mutation snapshots are deduplicated.
  assert.equal(layoutReads, 0, "Recording must not force layout before the failure");
  const initial = window.__tailscaleDiagnostics();
  assert.equal(initial.entries[0].key, "Enter");
  assert.equal(initial.entries[0].focus, "share");
  assert.equal(initial.entries[0].target, "share");
  assert.equal(initial.entries.filter((entry) => entry.event === "mutation").length, 1);
  const originalShareGeneration = initial.entries.at(-1).shareGeneration;
  share = item("Share");
  document.activeElement = share;
  observer();
  assert.notEqual(window.__tailscaleDiagnostics().entries.at(-1).shareGeneration, originalShareGeneration);
  present = false;
  panel.isConnected = false;
  observer();
  for (let index = 0; index < 100; index++) handlers.get("keyup")({ key: secret, target: item(secret) });
  const report = JSON.parse(JSON.stringify(window.__tailscaleDiagnostics()));
  assert.equal(report.owner, "FooterPart/FooterItem/ContributionToggle");
  assert.equal(report.entries.length, 96);
  assert.equal(report.entries.at(-1).region, false);
  assert.equal(report.entries.at(-1).width, 390);
  assert.equal(report.entries.at(-1).height, 844);
  assert.equal(report.entries.at(-1).focus, "other");
  assert.equal(report.geometry.region, null);
  assert.equal(JSON.stringify(report).includes(secret), false);
  assert.equal(report.entries.at(-2).key, "other");
  assert.ok(layoutReads > 0);
});
