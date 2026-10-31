// Activity card, in Node with a minimal DOM: its live subscription and the text of its entries.
// Run by tests/test_frontend.py (pytest), or directly: node --test tests/js/
import assert from "node:assert/strict";
import { test } from "node:test";

class FakeNode {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.className = "";
    this.textContent = "";
    this.classList = { add: (c) => (this.className += ` ${c}`) };
  }
  append(...nodes) {
    this.children.push(...nodes);
  }
  addEventListener() {}
}

class FakeShadowRoot extends FakeNode {
  set innerHTML(_html) {
    this.children = [];
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
