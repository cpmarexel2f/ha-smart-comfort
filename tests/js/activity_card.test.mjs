// Activity card, in Node with a minimal DOM: its live subscription and the text of its entries.
// Run by tests/test_frontend.py (pytest), or directly: node --test tests/js/
import assert from "node:assert/strict";
import { test } from "node:test";

let focused = null;

class FakeNode {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.className = "";
    this.textContent = "";
    this.attributes = {};
    this.dataset = {};
    this.listeners = {};
    this.classList = { add: (c) => (this.className += ` ${c}`) };
  }
  append(...nodes) {
    for (const node of nodes) node.parent = this;
    this.children.push(...nodes);
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }
  getAttribute(name) {
    return this.attributes[name] ?? null;
  }
  addEventListener(type, listener) {
    (this.listeners[type] ||= []).push(listener);
  }
  /** Fires `type` on this node; returns the event, to see whether its default was prevented. */
  fire(type, init = {}) {
    const event = { type, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...init };
    for (const listener of this.listeners[type] || []) listener(event);
    return event;
  }
  focus() {
    focused = this;
  }
}

class FakeShadowRoot extends FakeNode {
  set innerHTML(_html) {
    for (const child of this.children) child.parent = null;
    this.children = [];
  }
  /** The focused node, while it is still in this tree. */
  get activeElement() {
    let node = focused;
    while (node && node !== this) node = node.parent;
    return node ? focused : null;
  }
}

globalThis.window = globalThis;
globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = new FakeShadowRoot("#shadow-root");
    return this.shadowRoot;
  }
  get isConnected() {
    return Boolean(this._attached);
  }
  dispatchEvent() {}
};
const registry = new Map();
globalThis.customElements = {
  get: (name) => registry.get(name),
  define: (name, cls) => registry.set(name, cls),
  whenDefined: async (name) => registry.get(name),
};
globalThis.document = { createElement: (tag) => new FakeNode(tag), querySelector: () => null };

await import("../../custom_components/smart_comfort/frontend/smart-comfort-activity-card.js");
const Card = customElements.get("smart-comfort-activity-card");

/** A connection whose subscriptions resolve on demand (`settle`) or right away, and fail when asked. */
function fakeHass({ fail = false } = {}) {
  const subs = [];
  const pending = [];
  const connection = {
    subscribeMessage(callback) {
      const sub = { callback, open: true };
      subs.push(sub);
      return new Promise((resolve, reject) => {
        pending.push(() => (fail ? reject(new Error("unknown command")) : resolve(() => (sub.open = false))));
      });
    },
  };
  return {
    hass: { language: "en", states: {}, connection },
    subs,
    open: () => subs.filter((s) => s.open),
    /** Resolve every subscription made so far, then let the card's awaits run. */
    async settle() {
      while (pending.length) pending.shift()();
      await new Promise((r) => setTimeout(r, 0));
    },
    /** What the server pushes, to every subscription still open (the server does not know about the others). */
    push(msg) {
      for (const sub of subs) if (sub.open) sub.callback(msg);
    },
  };
}

function attach(card) {
  card._attached = true;
  card.connectedCallback();
}

function detach(card) {
  card._attached = false;
  card.disconnectedCallback();
}

function walk(node, out = []) {
  out.push(node);
  for (const child of node.children || []) walk(child, out);
  return out;
}

const rows = (card) => walk(card.shadowRoot).filter((n) => /(^| )row( |$)/.test(n.className));
const texts = (card) =>
  walk(card.shadowRoot)
    .filter((n) => n.className === "what")
    .map((n) => n.textContent);

const entry = (extra) => ({ at: new Date().toISOString(), kind: "device", ...extra });

test("Lovelace order (hass before the card is attached): one subscription, each entry once", async () => {
  const fake = fakeHass();
  const card = new Card();
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  await fake.settle();
  assert.equal(fake.subs.length, 1);
  fake.push({ entries: [] });
  fake.push({ added: [entry({ target: "cool" })] });
  assert.equal(rows(card).length, 1);
  detach(card);
  assert.equal(fake.open().length, 0);
});

test("panel order (attached, then hass): one subscription, closed when detached", async () => {
  const fake = fakeHass();
  const card = new Card();
  attach(card);
  card.setConfig({ panel: true });
  card.hass = fake.hass;
  card.hass = fake.hass;
  await fake.settle();
  assert.equal(fake.subs.length, 1);
  detach(card);
  assert.equal(fake.open().length, 0);
});

test("detached before the subscription is ready: it is closed as soon as it is", async () => {
  const fake = fakeHass();
  const card = new Card();
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  detach(card);
  await fake.settle();
  assert.equal(fake.open().length, 0);
  // Back on the view: subscribed again, once.
  attach(card);
  await fake.settle();
  assert.equal(fake.open().length, 1);
  fake.push({ added: [entry({ target: "cool" })] });
  assert.equal(rows(card).length, 1);
});

test("back on the view after leaving it: subscribed again", async () => {
  const fake = fakeHass();
  const card = new Card();
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  await fake.settle();
  detach(card);
  attach(card);
  await fake.settle();
  assert.equal(fake.subs.length, 2);
  assert.equal(fake.open().length, 1);
});

test("Smart Comfort not loaded: says so, and tries again when attached again", async () => {
  const fake = fakeHass({ fail: true });
  const card = new Card();
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  await fake.settle();
  assert.deepEqual(texts(card), []);
  assert.ok(walk(card.shadowRoot).some((n) => n.textContent === "Smart Comfort is not loaded."));
  detach(card);
  attach(card);
  await fake.settle();
  assert.equal(fake.subs.length, 2);
});

test("failed commands: what could not be sent, never a raw key", async () => {
  const fake = fakeHass();
  const card = new Card();
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  await fake.settle();
  fake.push({
    entries: [
      entry({ kind: "failed", target: "cool" }),
      entry({ kind: "failed", target: "presence" }),
      entry({ kind: "failed", target: "display_off" }),
      entry({ kind: "failed", target: "display_on" }),
      entry({ kind: "failed", target: "60 % · 2700 K" }),
      entry({ kind: "failed" }),
    ],
  });
  assert.deepEqual(texts(card), [
    "Could not be sent · Cooling",
    "Could not be sent · On: someone came in",
    "Could not be sent · Indicator off",
    "Could not be sent · Indicator back on",
    "Could not be sent · Brightness of the moment · 60 % · 2700 K",
    "Could not be sent",
  ]);
});

/** A card of the panel's Activity tab, attached, with these entries. */
async function panelCard(entries) {
  const fake = fakeHass();
  const card = new Card();
  attach(card);
  card.setConfig({ panel: true });
  card.hass = fake.hass;
  await fake.settle();
  fake.push({ entries });
  return { card, fake };
}

const chip = (card, label) => walk(card.shadowRoot).find((n) => n.tagName === "button" && n.textContent === label);

test("Activity tab filters: a failed light command is under Lights, a failed device command under Devices", async () => {
  const { card } = await panelCard([
    entry({ kind: "failed", entity_id: "light.hall", action: "light.turn_on", target: "presence" }),
    entry({ kind: "failed", entity_id: "light.desk", action: "light.turn_on", target: "60 % · 2700 K" }),
    entry({ kind: "failed", entity_id: "climate.living", action: "climate.set_hvac_mode", target: "cool" }),
    // An indicator that is a light: an indicator, so a device.
    entry({ kind: "failed", entity_id: "light.ac_led", action: "light.turn_off", target: "display_off" }),
    entry({ kind: "failed" }),
  ]);
  chip(card, "Lights").fire("click");
  assert.deepEqual(texts(card), [
    "light.hall — Could not be sent · On: someone came in",
    "light.desk — Could not be sent · Brightness of the moment · 60 % · 2700 K",
  ]);
  chip(card, "Devices").fire("click");
  assert.deepEqual(texts(card), [
    "climate.living — Could not be sent · Cooling",
    "light.ac_led — Could not be sent · Indicator off",
    "Could not be sent",
  ]);
  chip(card, "All").fire("click");
  assert.equal(texts(card).length, 5);
});

test("a line that opens its entity is a button for the keyboard too (Enter and Space)", async () => {
  const fake = fakeHass();
  const card = new Card();
  const opened = [];
  card.dispatchEvent = (event) => opened.push(event.detail.entityId);
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  await fake.settle();
  fake.push({ entries: [entry({ entity_id: "fan.bedroom", target: "cool" }), entry({ kind: "reset" })] });
  const [withEntity, without] = rows(card);
  assert.equal(withEntity.getAttribute("role"), "button");
  assert.equal(withEntity.getAttribute("tabindex"), "0");
  assert.equal(without.getAttribute("role"), null);
  assert.equal(without.getAttribute("tabindex"), null);
  assert.ok(withEntity.fire("keydown", { key: "Enter" }).defaultPrevented);
  assert.ok(withEntity.fire("keydown", { key: " " }).defaultPrevented);
  assert.equal(withEntity.fire("keydown", { key: "Tab" }).defaultPrevented, false);
  withEntity.fire("click");
  assert.deepEqual(opened, ["fan.bedroom", "fan.bedroom", "fan.bedroom"]);
});

test("a new entry does not take the keyboard focus away from the line that has it", async () => {
  const fake = fakeHass();
  const card = new Card();
  card.setConfig({});
  card.hass = fake.hass;
  attach(card);
  await fake.settle();
  const first = entry({ entity_id: "fan.bedroom", target: "cool", at: "2026-11-01T10:00:00Z" });
  fake.push({ entries: [first] });
  rows(card)[0].focus();
  fake.push({ added: [entry({ entity_id: "climate.living", target: "off", at: "2026-11-01T10:05:00Z" })] });
  const focusedRow = card.shadowRoot.activeElement;
  assert.ok(focusedRow, "the focus is lost");
  assert.equal(focusedRow, rows(card)[1]);
  // A line that is gone (filtered out, or past the limit): nothing to focus, no error.
  card.setConfig({ limit: 1 });
  assert.equal(card.shadowRoot.activeElement, null);
});

test("a filter chosen with the keyboard keeps the focus", async () => {
  const { card } = await panelCard([entry({ entity_id: "fan.bedroom", target: "cool" })]);
  const lights = chip(card, "Lights");
  lights.focus();
  lights.fire("click");
  assert.equal(card.shadowRoot.activeElement, chip(card, "Lights"));
  assert.equal(chip(card, "Lights").getAttribute("aria-pressed"), "true");
  assert.equal(chip(card, "All").getAttribute("aria-pressed"), "false");
});

test("the active filter is tinted, not a filled button", async () => {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile(new URL("../../custom_components/smart_comfort/frontend/smart-comfort-activity-card.js", import.meta.url), "utf8");
  const rule = source.match(/\.chip\.active\s*\{([^}]*)\}/)?.[1];
  assert.ok(rule, "no .chip.active rule");
  assert.doesNotMatch(rule, /background:\s*var\(--primary-color\)/);
  assert.match(rule, /background:\s*rgba\(var\(--rgb-primary-color/);
  assert.doesNotMatch(rule, /--text-primary-color/);
});
