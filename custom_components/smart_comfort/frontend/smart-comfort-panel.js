/**
 * Smart Comfort — configuration panel.
 *
 * A plain web component (no build step) that Home Assistant loads in the sidebar. It reads and saves
 * the integration options over the WebSocket API (smart_comfort/config, smart_comfort/config/save),
 * follows the status (smart_comfort/subscribe) and renders the forms with Home Assistant's ha-form,
 * whose labels come from the integration's own translations (options flow strings).
 */

const DOMAIN = "smart_comfort";

const KIND_ICONS = {
  too_hot: "mdi:thermometer-high",
  close_windows: "mdi:window-closed-variant",
  ventilate: "mdi:window-open-variant",
  too_cold: "mdi:thermometer-low",
  window_open_cold: "mdi:snowflake-alert",
  co2_high: "mdi:molecule-co2",
  humidity_high: "mdi:water-percent-alert",
};

const UNITS = { co2_high: "ppm", humidity_high: "%" };

// Strings of the panel itself; field labels come from the integration translations.
const STRINGS = {
  en: {
    fan: "Fan",
    purifier: "Air purifier",
    overview: "Overview",
    rooms: "Rooms",
    alerts: "Alerts",
    notifications: "Notifications",
    control: "Device control",
    save: "Save",
    discard: "Discard",
    saved: "Saved",
    saving: "Saving…",
    unsaved: "Unsaved changes",
    yaml: "This configuration comes from YAML. Changes saved here stay until the YAML changes: then the YAML replaces them at the next restart.",
    not_loaded: "Smart Comfort is not loaded. Check the logs.",
    not_setup: "Smart Comfort is not set up yet: add it in Settings → Devices & services.",
    active_alerts: "Active alerts",
    no_alerts: "Everything is fine.",
    outdoor: "Outdoor",
    notifications_on: "Notifications on",
    notifications_off: "Notifications off",
    control_on: "Device control on",
    control_off: "Device control off",
    notify_now: "Notify now",
    unsnooze: "Cancel snoozes",
    snooze: "Snooze",
    acknowledge: "Got it",
    snoozed: "snoozed",
    acknowledged: "acknowledged",
    handled: "handled",
    notified: "notified",
    pending: "not notified yet",
    since: "since",
    ok: "OK",
    open: "Open",
    devices: "Devices",
    target: "target",
    manual: "manual until",
    last_notification: "Last notification",
    add_room: "Add a room",
    new_room: "New room",
    remove: "Remove",
    move_up: "Move up",
    move_down: "Move down",
    room_alerts: "Alerts of this room",
    room_alerts_help: "Empty fields use the settings of the Alerts tab.",
    inherit: "Default",
    enabled: "On",
    disabled: "Off",
    climate: "Air conditioner",
    fans: "Fans",
    purifiers: "Air purifiers",
    add_fan: "Add a fan",
    add_purifier: "Add a purifier",
    device_settings: "Settings of this device",
    default_value: "Default: {value}",
    no_rooms: "No room yet.",
    sensors: "Sensors",
  },
  fr: {
    fan: "Ventilateur",
    purifier: "Purificateur",
    overview: "Vue d'ensemble",
    rooms: "Pièces",
    alerts: "Alertes",
    notifications: "Notifications",
    control: "Pilotage des appareils",
    save: "Enregistrer",
    discard: "Annuler",
    saved: "Enregistré",
    saving: "Enregistrement…",
    unsaved: "Modifications non enregistrées",
    yaml: "Cette configuration vient du YAML. Ce qui est enregistré ici reste jusqu'à ce que le YAML change : il le remplace alors au prochain redémarrage.",
    not_loaded: "Smart Comfort n'est pas chargé. Consultez les journaux.",
    not_setup: "Smart Comfort n'est pas encore configuré : ajoutez-le dans Paramètres → Appareils et services.",
    active_alerts: "Alertes actives",
    no_alerts: "Tout va bien.",
    outdoor: "Extérieur",
    notifications_on: "Notifications activées",
    notifications_off: "Notifications coupées",
    control_on: "Pilotage activé",
    control_off: "Pilotage coupé",
    notify_now: "Notifier maintenant",
    unsnooze: "Annuler les sourdines",
    snooze: "Ignorer",
    acknowledge: "C'est noté",
    snoozed: "en sourdine",
    acknowledged: "acquittée",
    handled: "traitée",
    notified: "notifiée",
    pending: "pas encore notifiée",
    since: "depuis",
    ok: "OK",
    open: "Ouvert",
    devices: "Appareils",
    target: "cible",
    manual: "manuel jusqu'à",
    last_notification: "Dernière notification",
    add_room: "Ajouter une pièce",
    new_room: "Nouvelle pièce",
    remove: "Supprimer",
    move_up: "Monter",
    move_down: "Descendre",
    room_alerts: "Alertes de cette pièce",
    room_alerts_help: "Les champs vides reprennent les réglages de l'onglet Alertes.",
    inherit: "Par défaut",
    enabled: "Activée",
    disabled: "Désactivée",
    climate: "Climatiseur",
    fans: "Ventilateurs",
    purifiers: "Purificateurs d'air",
    add_fan: "Ajouter un ventilateur",
    add_purifier: "Ajouter un purificateur",
    device_settings: "Réglages de cet appareil",
    default_value: "Par défaut : {value}",
    no_rooms: "Aucune pièce pour l'instant.",
    sensors: "Capteurs",
  },
  de: {
    fan: "Lüfter",
    purifier: "Luftreiniger",
    overview: "Übersicht",
    rooms: "Räume",
    alerts: "Meldungen",
    notifications: "Benachrichtigungen",
    control: "Gerätesteuerung",
    save: "Speichern",
    discard: "Verwerfen",
    saved: "Gespeichert",
    saving: "Speichern…",
    unsaved: "Ungespeicherte Änderungen",
    yaml: "Diese Konfiguration stammt aus YAML. Hier gespeicherte Änderungen bleiben, bis sich das YAML ändert: dann ersetzt es sie beim nächsten Neustart.",
    not_loaded: "Smart Comfort ist nicht geladen. Prüfen Sie die Protokolle.",
    not_setup: "Smart Comfort ist noch nicht eingerichtet: unter Einstellungen → Geräte & Dienste hinzufügen.",
    active_alerts: "Aktive Meldungen",
    no_alerts: "Alles in Ordnung.",
    outdoor: "Außen",
    notifications_on: "Benachrichtigungen an",
    notifications_off: "Benachrichtigungen aus",
    control_on: "Gerätesteuerung an",
    control_off: "Gerätesteuerung aus",
    notify_now: "Jetzt benachrichtigen",
    unsnooze: "Stummschaltungen aufheben",
    snooze: "Stumm",
    acknowledge: "Verstanden",
    snoozed: "stumm",
    acknowledged: "bestätigt",
    handled: "behandelt",
    notified: "gemeldet",
    pending: "noch nicht gemeldet",
    since: "seit",
    ok: "OK",
    open: "Offen",
    devices: "Geräte",
    target: "Ziel",
    manual: "manuell bis",
    last_notification: "Letzte Benachrichtigung",
    add_room: "Raum hinzufügen",
    new_room: "Neuer Raum",
    remove: "Entfernen",
    move_up: "Nach oben",
    move_down: "Nach unten",
    room_alerts: "Meldungen dieses Raums",
    room_alerts_help: "Leere Felder übernehmen die Einstellungen des Reiters Meldungen.",
    inherit: "Standard",
    enabled: "An",
    disabled: "Aus",
    climate: "Klimaanlage",
    fans: "Lüfter",
    purifiers: "Luftreiniger",
    add_fan: "Lüfter hinzufügen",
    add_purifier: "Luftreiniger hinzufügen",
    device_settings: "Einstellungen dieses Geräts",
    default_value: "Standard: {value}",
    no_rooms: "Noch kein Raum.",
    sensors: "Sensoren",
  },
  es: {
    fan: "Ventilador",
    purifier: "Purificador",
    overview: "Resumen",
    rooms: "Estancias",
    alerts: "Alertas",
    notifications: "Notificaciones",
    control: "Control de aparatos",
    save: "Guardar",
    discard: "Descartar",
    saved: "Guardado",
    saving: "Guardando…",
    unsaved: "Cambios sin guardar",
    yaml: "Esta configuración viene de YAML. Lo guardado aquí se mantiene hasta que cambie el YAML: entonces lo sustituye en el próximo reinicio.",
    not_loaded: "Smart Comfort no está cargado. Revise los registros.",
    not_setup: "Smart Comfort aún no está configurado: añádalo en Ajustes → Dispositivos y servicios.",
    active_alerts: "Alertas activas",
    no_alerts: "Todo va bien.",
    outdoor: "Exterior",
    notifications_on: "Notificaciones activadas",
    notifications_off: "Notificaciones desactivadas",
    control_on: "Control activado",
    control_off: "Control desactivado",
    notify_now: "Notificar ahora",
    unsnooze: "Cancelar pausas",
    snooze: "Posponer",
    acknowledge: "Entendido",
    snoozed: "pospuesta",
    acknowledged: "confirmada",
    handled: "gestionada",
    notified: "notificada",
    pending: "aún no notificada",
    since: "desde",
    ok: "OK",
    open: "Abierto",
    devices: "Aparatos",
    target: "objetivo",
    manual: "manual hasta",
    last_notification: "Última notificación",
    add_room: "Añadir una estancia",
    new_room: "Nueva estancia",
    remove: "Eliminar",
    move_up: "Subir",
    move_down: "Bajar",
    room_alerts: "Alertas de esta estancia",
    room_alerts_help: "Los campos vacíos usan los ajustes de la pestaña Alertas.",
    inherit: "Por defecto",
    enabled: "Activada",
    disabled: "Desactivada",
    climate: "Aire acondicionado",
    fans: "Ventiladores",
    purifiers: "Purificadores de aire",
    add_fan: "Añadir un ventilador",
    add_purifier: "Añadir un purificador",
    device_settings: "Ajustes de este aparato",
    default_value: "Por defecto: {value}",
    no_rooms: "Aún no hay estancias.",
    sensors: "Sensores",
  },
};

const TABS = ["overview", "rooms", "alerts", "notifications", "control"];

const clone = (value) => (value === undefined ? undefined : JSON.parse(JSON.stringify(value)));
const isEmpty = (v) => v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);

/** Drop empty values, recursively; empty objects go too. */
function prune(value) {
  if (Array.isArray(value)) return value.map(prune);
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, v] of Object.entries(value)) {
      const p = prune(v);
      if (isEmpty(p) || (p && typeof p === "object" && !Array.isArray(p) && Object.keys(p).length === 0)) continue;
      out[key] = p;
    }
    return out;
  }
  return value;
}

const TIME = /^\d{1,2}:\d{2}(:\d{2})?$/;
/** Same value for the options: "09:00" and "09:00:00" are the same time. */
function same(a, b) {
  if (typeof a === "string" && typeof b === "string" && TIME.test(a) && TIME.test(b)) {
    const norm = (t) => t.split(":").map((x) => x.padStart(2, "0")).concat(["00"]).slice(0, 3).join(":");
    return norm(a) === norm(b);
  }
  return JSON.stringify(a) === JSON.stringify(b);
}

/** The keys of value that differ from defaults (defaults are what a missing key means). */
function diff(value, defaults) {
  const out = {};
  for (const [key, v] of Object.entries(value || {})) {
    const d = defaults ? defaults[key] : undefined;
    if (v && typeof v === "object" && !Array.isArray(v) && d && typeof d === "object") {
      const sub = diff(v, d);
      if (Object.keys(sub).length) out[key] = sub;
    } else if (!isEmpty(v) && !same(v, d)) {
      out[key] = v;
    }
  }
  return out;
}

/** Defaults with the values set on top, nested one level for the device sections. */
function merged(defaults, values) {
  const out = { ...clone(defaults) };
  for (const [key, v] of Object.entries(values || {})) {
    if (v && typeof v === "object" && !Array.isArray(v) && out[key] && typeof out[key] === "object") {
      out[key] = { ...out[key], ...v };
    } else {
      out[key] = v;
    }
  }
  return out;
}

const num = (unit, opts = {}) => ({
  number: { mode: "box", step: opts.step ?? 0.1, min: opts.min ?? -50, max: opts.max ?? 5000, unit_of_measurement: unit },
});
const minutes = (min = 0) => ({ number: { mode: "box", step: 1, min, max: 1440, unit_of_measurement: "min" } });
const percent = { number: { mode: "slider", step: 1, min: 0, max: 100, unit_of_measurement: "%" } };
const text = { text: {} };
const bool = { boolean: {} };
const time = { time: {} };
const entity = (domain, extra = {}) => ({ entity: { domain, ...extra } });

let haFormLoading;
/** ha-form and the entity pickers are lazy-loaded by Home Assistant: load them through a card editor. */
function loadHaForm() {
  if (customElements.get("ha-form")) return Promise.resolve();
  if (!haFormLoading) {
    haFormLoading = (async () => {
      if (window.loadCardHelpers) {
        const helpers = await window.loadCardHelpers();
        const card = await helpers.createCardElement({ type: "entities", entities: [] });
        if (card?.constructor?.getConfigElement) await card.constructor.getConfigElement();
      }
      await customElements.whenDefined("ha-form");
    })();
  }
  return haFormLoading;
}

class SmartComfortPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "overview";
    this._config = null; // smart_comfort/config result
    this._draft = null; // options being edited
    this._status = null;
    this._labels = {};
    this._selector = {};
    this._forms = [];
    this._message = null;
    this._saving = false;
    this._expanded = new Set();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    for (const form of this._forms) form.hass = hass;
    if (first) this._init();
  }

  get hass() {
    return this._hass;
  }

  /** /smart-comfort/<tab> opens that tab. */
  set route(route) {
    const tab = (route?.path || "").split("/").filter(Boolean)[0];
    if (TABS.includes(tab) && tab !== this._tab) {
      this._tab = tab;
      if (this._config !== null || this._error) this._render();
    }
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menu) this._menu.narrow = narrow;
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  // Strings.

  _t(key, values = {}) {
    const lang = (this._hass?.language || "en").split("-")[0];
    let s = (STRINGS[lang] || STRINGS.en)[key] ?? STRINGS.en[key] ?? key;
    for (const [k, v] of Object.entries(values)) s = s.replace(`{${k}}`, v);
    return s;
  }

  _label(step, name, section) {
    const base = `component.${DOMAIN}.options.step.${step}`;
    const r = this._labels;
    return (
      (section && r[`${base}.sections.${section}.data.${name}`]) || r[`${base}.data.${name}`] || name
    );
  }

  _helper(step, name, section) {
    const base = `component.${DOMAIN}.options.step.${step}`;
    const r = this._labels;
    return (section && r[`${base}.sections.${section}.data_description.${name}`]) || r[`${base}.data_description.${name}`];
  }

  _sectionTitle(step, section) {
    return this._labels[`component.${DOMAIN}.options.step.${step}.sections.${section}.name`] || section;
  }

  _kindName(kind) {
    return this._selector[`component.${DOMAIN}.selector.kind.options.${kind}`] || kind;
  }

  _options(selector, values) {
    return values.map((value) => ({
      value,
      label: this._selector[`component.${DOMAIN}.selector.${selector}.options.${value}`] || value,
    }));
  }

  // Data.

  async _init() {
    const language = this._hass.language || "en";
    const get = (category) =>
      this._hass
        .callWS({ type: "frontend/get_translations", language, category, integration: [DOMAIN] })
        .then((r) => r.resources)
        .catch(() => ({}));
    const [labels, selector] = await Promise.all([get("options"), get("selector"), loadHaForm()]);
    this._labels = labels;
    this._selector = selector;
    await this._load();
    this._subscribe();
  }

  async _load() {
    try {
      this._config = await this._hass.callWS({ type: `${DOMAIN}/config` });
      this._draft = clone(this._config.options);
      this._error = null;
    } catch (err) {
      this._config = null;
      this._error = err.code === "not_found" ? this._t("not_setup") : err.message;
    }
    this._render();
  }

  _subscribe() {
    if (this._unsub || !this._hass) return;
    this._unsub = this._hass.connection.subscribeMessage(
      (msg) => {
        this._status = msg.status;
        if (this._tab === "overview") this._renderTab();
      },
      { type: `${DOMAIN}/subscribe` }
    );
    this._unsub.catch(() => {
      this._unsub = null;
    });
  }

  get _dirty() {
    if (!this._config) return false;
    return JSON.stringify(prune(this._draft)) !== JSON.stringify(prune(this._config.options));
  }

  async _save() {
    this._saving = true;
    this._message = null;
    this._renderToolbar();
    try {
      const result = await this._hass.callWS({ type: `${DOMAIN}/config/save`, options: prune(this._draft) });
      this._config.options = result.options;
      this._draft = clone(result.options);
      this._message = { type: "success", text: this._t("saved") };
    } catch (err) {
      this._message = { type: "error", text: err.message };
    }
    this._saving = false;
    this._render();
  }

  _discard() {
    this._draft = clone(this._config.options);
    this._message = null;
    this._render();
  }

  _changed() {
    this._renderToolbar();
  }

  // Rendering.

  _render() {
    const root = this.shadowRoot;
    root.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar">
        <span class="menu"></span>
        <div class="title">Smart Comfort</div>
        <div class="actions"></div>
      </div>
      <div class="tabs" role="tablist"></div>
      <div class="content"></div>`;
    const menu = document.createElement("ha-menu-button");
    menu.hass = this._hass;
    menu.narrow = this._narrow;
    this._menu = menu;
    root.querySelector(".menu").append(menu);
    const tabs = root.querySelector(".tabs");
    for (const tab of TABS) {
      const b = document.createElement("button");
      b.className = `tab${tab === this._tab ? " active" : ""}`;
      b.setAttribute("role", "tab");
      b.textContent = this._t(tab);
      b.addEventListener("click", () => {
        this._tab = tab;
        const base = (this.panel?.url_path || "smart-comfort").replace(/^\//, "");
        history.replaceState(history.state, "", `/${base}${tab === "overview" ? "" : `/${tab}`}`);
        this._render();
      });
      tabs.append(b);
    }
    this._renderToolbar();
    this._renderTab();
  }

  _renderToolbar() {
    const actions = this.shadowRoot.querySelector(".actions");
    if (!actions) return;
    actions.innerHTML = "";
    if (this._dirty) {
      const note = document.createElement("span");
      note.className = "dirty";
      note.textContent = this._t("unsaved");
      actions.append(note, this._button(this._t("discard"), () => this._discard()));
      const save = this._button(this._saving ? this._t("saving") : this._t("save"), () => this._save(), "primary");
      save.disabled = this._saving;
      actions.append(save);
    }
  }

  _button(label, onClick, kind = "") {
    const b = document.createElement("button");
    b.className = `btn ${kind}`;
    b.textContent = label;
    b.addEventListener("click", onClick);
    return b;
  }

  _iconButton(icon, label, onClick) {
    const b = document.createElement("button");
    b.className = "icon-btn";
    b.title = label;
    b.setAttribute("aria-label", label);
    const i = document.createElement("ha-icon");
    i.icon = icon;
    b.append(i);
    b.addEventListener("click", onClick);
    return b;
  }

  _el(tag, cls, content) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (content !== undefined) e.textContent = content;
    return e;
  }

  _card(title, icon) {
    const card = this._el("div", "card");
    if (title) {
      const h = this._el("div", "card-header");
      if (icon) {
        const i = document.createElement("ha-icon");
        i.icon = icon;
        h.append(i);
      }
      h.append(this._el("span", "", title));
      card.append(h);
    }
    return card;
  }

  _form(schema, data, onChange, label, helper) {
    const form = document.createElement("ha-form");
    form.hass = this._hass;
    form.schema = schema;
    form.data = data;
    form.computeLabel = label;
    if (helper) form.computeHelper = helper;
    form.addEventListener("value-changed", (ev) => {
      ev.stopPropagation();
      const value = ev.detail.value;
      form.data = value;
      onChange(value);
      this._changed();
    });
    this._forms.push(form);
    return form;
  }

  _renderTab() {
    const content = this.shadowRoot.querySelector(".content");
    if (!content) return;
    content.innerHTML = "";
    this._forms = [];
    if (this._message) {
      content.append(this._el("div", `banner ${this._message.type}`, this._message.text));
    }
    if (!this._config) {
      content.append(this._el("div", "banner error", this._error || "…"));
      return;
    }
    if (this._config.yaml && this._tab !== "overview") {
      content.append(this._el("div", "banner info", this._t("yaml")));
    }
    const render = {
      overview: () => this._renderOverview(content),
      rooms: () => this._renderRooms(content),
      alerts: () => this._renderAlerts(content),
      notifications: () => this._renderGeneral(content),
      control: () => this._renderControl(content),
    }[this._tab];
    render();
  }

  // Overview.

  _format(value, digits = 1) {
    if (typeof value !== "number") return "–";
    return value.toLocaleString(this._hass.language, { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  }

  _time(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const today = new Date().toDateString() === d.toDateString();
    return today
      ? d.toLocaleTimeString(this._hass.language, { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleString(this._hass.language, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  _service(service, data = {}) {
    return this._hass.callService(DOMAIN, service, data);
  }

  _renderOverview(content) {
    const s = this._status;
    if (!this._config.loaded || !s) {
      content.append(this._el("div", "banner error", this._t("not_loaded")));
      return;
    }
    const summary = this._el("div", "summary");
    const tile = (icon, label, value, onClick, active) => {
      const t = this._el(onClick ? "button" : "div", `tile${active === false ? " off" : ""}`);
      const i = document.createElement("ha-icon");
      i.icon = icon;
      t.append(i, this._el("div", "tile-value", value), this._el("div", "tile-label", label));
      if (onClick) t.addEventListener("click", onClick);
      return t;
    };
    summary.append(
      tile("mdi:alert-circle-outline", this._t("active_alerts"), String(s.alerts.length)),
      tile("mdi:home-thermometer-outline", this._t("outdoor"), `${this._format(s.outdoor_temperature)} °C`),
      tile(
        s.notifications_enabled ? "mdi:bell" : "mdi:bell-off",
        this._t(s.notifications_enabled ? "notifications_on" : "notifications_off"),
        "",
        () =>
          this._hass.callService("switch", s.notifications_enabled ? "turn_off" : "turn_on", {
            entity_id: this._switch("notifications"),
          }),
        s.notifications_enabled
      ),
      tile(
        s.control_enabled ? "mdi:air-conditioner" : "mdi:hand-back-right-off",
        this._t(s.control_enabled ? "control_on" : "control_off"),
        "",
        () =>
          this._hass.callService("switch", s.control_enabled ? "turn_off" : "turn_on", {
            entity_id: this._switch("control"),
          }),
        s.control_enabled
      )
    );
    content.append(summary);

    const alerts = this._card(this._t("active_alerts"), "mdi:bell-ring-outline");
    if (!s.alerts.length) {
      alerts.append(this._el("div", "empty", this._t("no_alerts")));
    }
    for (const a of s.alerts) {
      const row = this._el("div", "alert");
      const i = document.createElement("ha-icon");
      i.icon = KIND_ICONS[a.kind] || "mdi:alert";
      i.className = `kind ${a.kind}`;
      const body = this._el("div", "alert-body");
      body.append(this._el("div", "alert-title", `${a.room_name} · ${this._kindName(a.kind)}`));
      const unit = UNITS[a.kind] || "°C";
      const value = a.kind === "ventilate" || a.kind === "close_windows" ? a.temperature : a.value;
      const parts = [`${this._format(value, a.kind === "co2_high" ? 0 : 1)} ${unit}`];
      parts.push(`${this._t("since")} ${this._time(a.since)}`);
      parts.push(a.notified_at ? `${this._t("notified")} ${this._time(a.notified_at)}` : this._t("pending"));
      body.append(this._el("div", "alert-meta", parts.join(" · ")));
      const badges = this._el("div", "badges");
      for (const flag of ["snoozed", "acknowledged", "handled"]) {
        if (a[flag]) badges.append(this._el("span", `badge ${flag}`, this._t(flag)));
      }
      body.append(badges);
      const actions = this._el("div", "row-actions");
      actions.append(
        this._iconButton("mdi:alarm-snooze", this._t("snooze"), () =>
          this._service("snooze", { rooms: [a.room], kinds: [a.kind] })
        ),
        this._iconButton("mdi:check", this._t("acknowledge"), () =>
          this._service("acknowledge", { rooms: [a.room], kinds: [a.kind] })
        )
      );
      row.append(i, body, actions);
      alerts.append(row);
    }
    const footer = this._el("div", "card-actions");
    footer.append(this._button(this._t("notify_now"), () => this._service("notify_now")));
    if (Object.keys(s.snoozes || {}).length || s.alerts.some((a) => a.snoozed)) {
      footer.append(this._button(this._t("unsnooze"), () => this._service("unsnooze")));
    }
    alerts.append(footer);
    content.append(alerts);

    const grid = this._el("div", "grid");
    for (const room of s.rooms) {
      const card = this._card(room.name, room.alerts.length ? KIND_ICONS[room.alerts[0]] : "mdi:home-heart");
      card.classList.add(room.alerts.length ? "has-alert" : "is-ok");
      const chips = this._el("div", "chips");
      const chip = (icon, value) => {
        const c = this._el("span", "chip");
        const i = document.createElement("ha-icon");
        i.icon = icon;
        c.append(i, document.createTextNode(value));
        chips.append(c);
      };
      if (room.temperature !== null) chip("mdi:thermometer", `${this._format(room.temperature)} °C`);
      if (room.co2 !== null) chip("mdi:molecule-co2", `${this._format(room.co2, 0)} ppm`);
      if (room.humidity !== null) chip("mdi:water-percent", `${this._format(room.humidity, 0)} %`);
      if (room.open?.length) {
        chip("mdi:window-open-variant", `${this._t("open")} (${room.open.length})`);
      }
      card.append(chips);
      card.append(
        this._el(
          "div",
          "room-status",
          room.alerts.length ? room.alerts.map((k) => this._kindName(k)).join(", ") : this._t("ok")
        )
      );
      const devices = Object.entries(room.devices || {});
      if (devices.length) {
        const list = this._el("div", "devices");
        for (const [entityId, d] of devices) {
          const state = this._hass.states[entityId];
          const line = this._el("div", "device");
          const name = state?.attributes?.friendly_name || entityId;
          line.append(this._el("span", "device-name", name));
          const info = [state ? this._hass.formatEntityState?.(state) ?? state.state : "–"];
          if (d.target) info.push(`${this._t("target")} ${d.target}`);
          if (d.override_until) info.push(`${this._t("manual")} ${this._time(d.override_until)}`);
          line.append(this._el("span", "device-state", info.join(" · ")));
          list.append(line);
        }
        card.append(list);
      }
      grid.append(card);
    }
    content.append(grid);

    if (s.last_notification) {
      const last = this._card(this._t("last_notification"), "mdi:bell-outline");
      last.append(this._el("div", "last-title", s.last_notification.title || ""));
      last.append(this._el("div", "last-message", s.last_notification.message || ""));
      last.append(this._el("div", "alert-meta", this._time(s.last_notification.at)));
      content.append(last);
    }
  }

  _switch(key) {
    const entries = Object.values(this._hass.entities || {}).filter(
      (e) => e.platform === DOMAIN && e.entity_id.startsWith("switch.")
    );
    const found = entries.find((e) => e.translation_key === key);
    if (found) return found.entity_id;
    return key === "control" ? "switch.smart_comfort_device_control" : "switch.smart_comfort_notifications";
  }

  // Notifications (general options).

  _renderGeneral(content) {
    const d = this._config.defaults.general;
    const o = this._draft;
    const notify = Object.keys(this._hass.services.notify || {})
      .filter((n) => !["send_message", "persistent_notification"].includes(n))
      .map((n) => `notify.${n}`);
    const current = o.notify || [];
    const schema = [
      {
        name: "notify",
        selector: {
          select: { multiple: true, custom_value: true, mode: "dropdown", options: [...new Set([...notify, ...current])].sort() },
        },
      },
      { name: "outdoor_temperature", selector: entity(["sensor", "weather"], { multiple: true }) },
      { name: "outdoor_aggregate", selector: { select: { mode: "dropdown", options: this._options("outdoor_aggregate", this._config.aggregates) } } },
      { name: "digest_window", selector: minutes() },
      { name: "reminder", selector: minutes() },
      { name: "snooze_duration", selector: minutes(1) },
      { name: "startup_grace", selector: minutes() },
      { name: "quiet_start", selector: time },
      { name: "quiet_end", selector: time },
      { name: "presence", selector: entity(["zone", "person", "group", "binary_sensor", "input_boolean", "device_tracker"]) },
      { name: "clear_when_resolved", selector: bool },
      { name: "critical_volume", selector: { number: { mode: "slider", min: 0, max: 1, step: 0.05 } } },
      { name: "url", selector: text },
      { name: "tag", selector: text },
    ];
    const keys = schema.map((s) => s.name);
    const data = merged(d, Object.fromEntries(keys.filter((key) => key in o).map((key) => [key, o[key]])));
    const card = this._card(this._t("notifications"), "mdi:bell-cog-outline");
    card.append(
      this._form(
        schema,
        data,
        (value) => {
          const changed = diff(value, d);
          for (const key of keys) delete this._draft[key];
          Object.assign(this._draft, changed);
        },
        (s) => this._label("general", s.name),
        (s) => this._helper("general", s.name)
      )
    );
    content.append(card);
  }

  // Alerts.

  _alertSchema(kind, defaults, inherit = false) {
    const unit = UNITS[kind] || "°C";
    const fields = [];
    if (inherit) {
      fields.push({
        name: "enabled",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "", label: this._t("inherit") },
              { value: "on", label: this._t("enabled") },
              { value: "off", label: this._t("disabled") },
            ],
          },
        },
      });
    } else {
      fields.push({ name: "enabled", selector: bool });
    }
    if ("threshold" in defaults) fields.push({ name: "threshold", selector: num(unit) });
    for (const key of ["min_indoor", "min_outdoor", "max_outdoor"]) {
      if (key in defaults) fields.push({ name: key, selector: num("°C") });
    }
    fields.push(
      { name: "hysteresis", selector: num(unit, { min: 0 }) },
      { name: "delay", selector: minutes() },
      {
        name: "severity",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              ...(inherit ? [{ value: "", label: this._t("inherit") }] : []),
              ...this._options("severity", this._config.severities),
            ],
          },
        },
      },
      { name: "escalation", selector: num(unit, { min: 0 }) }
    );
    return fields;
  }

  _renderAlerts(content) {
    const defaults = this._config.defaults.alerts;
    for (const kind of this._config.kinds) {
      const card = this._card(this._kindName(kind), KIND_ICONS[kind]);
      const own = this._draft.alerts?.[kind] || {};
      card.append(
        this._form(
          this._alertSchema(kind, defaults[kind]),
          merged(defaults[kind], own),
          (value) => {
            const alerts = (this._draft.alerts = this._draft.alerts || {});
            alerts[kind] = diff(value, defaults[kind]);
            if (!Object.keys(alerts[kind]).length) delete alerts[kind];
          },
          (s) => this._label("alert", s.name),
          (s) => this._helper("alert", s.name)
        )
      );
      content.append(card);
    }
  }

  // Device control.

  _controlSchema() {
    const sec = (name, schema) => ({ type: "expandable", name, title: this._sectionTitle("control", name), schema });
    return [
      { name: "enabled", selector: bool },
      { name: "start", selector: time },
      { name: "end", selector: time },
      { name: "manual_override", selector: minutes() },
      { name: "suppress_when_handled", selector: bool },
      sec("climate", [
        { name: "cool_above", selector: num("°C") },
        { name: "off_below", selector: num("°C") },
        { name: "setpoint", selector: num("°C", { step: 0.5 }) },
        { name: "fan_mode", selector: text },
        { name: "closed_for", selector: minutes() },
        { name: "off_on_open", selector: minutes() },
      ]),
      sec("fans", [
        { name: "on_above", selector: num("°C") },
        { name: "off_below", selector: num("°C") },
        { name: "percentage", selector: percent },
        { name: "preset", selector: text },
        { name: "open_percentage", selector: percent },
        { name: "open_preset", selector: text },
        { name: "off_preset", selector: text },
      ]),
      sec("purifiers", [
        { name: "open_percentage", selector: percent },
        { name: "open_preset", selector: text },
        { name: "closed_preset", selector: text },
        { name: "keep_on", selector: bool },
      ]),
    ];
  }

  _controlLabel(schema) {
    if (schema.type === "expandable") return this._sectionTitle("control", schema.name);
    for (const section of [null, "climate", "fans", "purifiers"]) {
      const label = this._label("control", schema.name, section);
      if (label !== schema.name) return label;
    }
    return schema.name;
  }

  _controlHelper(schema) {
    for (const section of [null, "climate", "fans", "purifiers"]) {
      const help = this._helper("control", schema.name, section);
      if (help) return help;
    }
    return undefined;
  }

  _renderControl(content) {
    const defaults = this._config.defaults.control;
    const card = this._card(this._t("control"), "mdi:air-conditioner");
    card.append(
      this._form(
        this._controlSchema(),
        merged(defaults, this._draft.control || {}),
        (value) => {
          const changed = diff(value, defaults);
          if (Object.keys(changed).length) this._draft.control = changed;
          else delete this._draft.control;
        },
        (s) => this._controlLabel(s),
        (s) => this._controlHelper(s)
      )
    );
    content.append(card);
  }

  // Rooms.

  _attr(entityId, attribute) {
    const value = this._hass.states[entityId]?.attributes?.[attribute];
    return Array.isArray(value) ? value : [];
  }

  _choice(values, current) {
    const options = [...new Set([...values, ...(current ? [current] : [])])];
    return { select: { mode: "dropdown", custom_value: true, options } };
  }

  /** Device list item <-> form data: an entity id alone, or a dict with its own settings. */
  _item(raw) {
    return typeof raw === "string" ? { entity_id: raw } : { ...raw };
  }

  _store(item) {
    const p = prune(item);
    const keys = Object.keys(p);
    return keys.length === 1 && keys[0] === "entity_id" ? p.entity_id : p;
  }

  _renderRooms(content) {
    const rooms = (this._draft.rooms = this._draft.rooms || []);
    if (!rooms.length) content.append(this._el("div", "empty card", this._t("no_rooms")));
    rooms.forEach((room, index) => {
      content.append(this._roomCard(room, index, rooms));
    });
    const add = this._button(this._t("add_room"), () => {
      let name = this._t("new_room");
      let n = 2;
      while (rooms.some((r) => r.name === name)) name = `${this._t("new_room")} ${n++}`;
      rooms.push({ name });
      this._expanded.add(rooms.length - 1);
      this._changed();
      this._renderTab();
    });
    add.classList.add("add");
    content.append(add);
  }

  _roomCard(room, index, rooms) {
    const card = this._el("div", "card room");
    const header = this._el("div", "card-header room-header");
    const open = this._expanded.has(index);
    const toggle = this._el("button", "room-toggle");
    const chevron = document.createElement("ha-icon");
    chevron.icon = open ? "mdi:chevron-down" : "mdi:chevron-right";
    toggle.append(chevron, this._el("span", "", room.name || "—"));
    toggle.addEventListener("click", () => {
      if (open) this._expanded.delete(index);
      else this._expanded.add(index);
      this._renderTab();
    });
    header.append(toggle);
    const tools = this._el("div", "row-actions");
    const move = (to) => {
      [rooms[index], rooms[to]] = [rooms[to], rooms[index]];
      const wasOpen = this._expanded.has(index);
      const otherOpen = this._expanded.has(to);
      this._expanded.delete(index);
      this._expanded.delete(to);
      if (wasOpen) this._expanded.add(to);
      if (otherOpen) this._expanded.add(index);
      this._changed();
      this._renderTab();
    };
    if (index > 0) tools.append(this._iconButton("mdi:arrow-up", this._t("move_up"), () => move(index - 1)));
    if (index < rooms.length - 1) {
      tools.append(this._iconButton("mdi:arrow-down", this._t("move_down"), () => move(index + 1)));
    }
    tools.append(
      this._iconButton("mdi:delete-outline", this._t("remove"), () => {
        rooms.splice(index, 1);
        this._expanded = new Set([...this._expanded].filter((i) => i !== index).map((i) => (i > index ? i - 1 : i)));
        this._changed();
        this._renderTab();
      })
    );
    header.append(tools);
    card.append(header);
    if (!open) return card;

    const label = (s) => this._label("room", s.name);
    // Sensors.
    card.append(this._el("div", "subheader", this._t("sensors")));
    const base = ["name", "temperature", "co2", "humidity", "openings"];
    card.append(
      this._form(
        [
          { name: "name", required: true, selector: text },
          { name: "temperature", selector: entity("sensor", { device_class: "temperature" }) },
          { name: "co2", selector: entity("sensor", { device_class: "carbon_dioxide" }) },
          { name: "humidity", selector: entity("sensor", { device_class: "humidity" }) },
          { name: "openings", selector: entity("binary_sensor", { multiple: true }) },
        ],
        Object.fromEntries(base.filter((k) => k in room).map((k) => [k, room[k]])),
        (value) => {
          for (const key of base) {
            if (isEmpty(value[key])) delete room[key];
            else room[key] = value[key];
          }
          toggle.lastChild.textContent = room.name || "—";
        },
        label
      )
    );

    // Air conditioner.
    card.append(this._el("div", "subheader", this._t("climate")));
    const climate = room.climate ? this._item(room.climate) : {};
    const climateDefaults = this._effectiveControl(room, "climate");
    const climateForm = this._form(
      this._climateSchema(climate.entity_id),
      climate,
      (value) => {
        if (!value.entity_id) delete room.climate;
        else room.climate = this._store(value);
        climateForm.schema = this._climateSchema(value.entity_id);
      },
      (s) => {
        if (s.type === "expandable") return this._t("device_settings");
        return s.name === "entity_id" ? this._t("climate") : this._label("control", s.name, "climate");
      },
      (s) => this._defaultHelp(s, climateDefaults)
    );
    card.append(climateForm);

    // Fans and purifiers.
    for (const [key, add] of [
      ["fans", "add_fan"],
      ["purifiers", "add_purifier"],
    ]) {
      card.append(this._el("div", "subheader", this._t(key)));
      const items = Array.isArray(room[key]) ? room[key] : room[key] ? [room[key]] : [];
      const defaults = this._effectiveControl(room, key);
      items.forEach((raw, i) => {
        const item = this._item(raw);
        const line = this._el("div", "device-item");
        const schemaFor = (entityId, itemValue) =>
          key === "fans" ? this._fanSchema(entityId) : this._purifierSchema(itemValue);
        const form = this._form(
          schemaFor(item.entity_id, item),
          item,
          (value) => {
            items[i] = this._store(value);
            room[key] = items.filter((x) => x && (typeof x === "string" || x.entity_id));
            form.schema = schemaFor(value.entity_id, value);
          },
          (s) => (s.type === "expandable" ? this._t("device_settings") : this._deviceLabel(key, s.name)),
          (s) => this._defaultHelp(s, defaults)
        );
        line.append(form);
        line.append(
          this._iconButton("mdi:delete-outline", this._t("remove"), () => {
            items.splice(i, 1);
            if (items.length) room[key] = items;
            else delete room[key];
            this._changed();
            this._renderTab();
          })
        );
        card.append(line);
      });
      const addButton = this._button(this._t(add), () => {
        room[key] = [...items, { entity_id: "" }];
        this._renderTab();
      });
      addButton.classList.add("small");
      card.append(addButton);
    }

    // Alerts of the room.
    card.append(this._el("div", "subheader", this._t("room_alerts")));
    card.append(this._el("div", "help", this._t("room_alerts_help")));
    const globals = this._config.defaults.alerts;
    const roomAlerts = room.alerts || {};
    const schema = this._config.kinds.map((kind) => ({
      type: "expandable",
      name: kind,
      title: this._kindName(kind),
      icon: KIND_ICONS[kind],
      schema: this._alertSchema(kind, globals[kind], true),
    }));
    const data = {};
    for (const kind of this._config.kinds) {
      const own = { ...(roomAlerts[kind] || {}) };
      if ("enabled" in own) own.enabled = own.enabled ? "on" : "off";
      data[kind] = own;
    }
    card.append(
      this._form(
        schema,
        data,
        (value) => {
          const out = {};
          for (const kind of this._config.kinds) {
            const own = prune(value[kind] || {});
            if (own.enabled) own.enabled = own.enabled === "on";
            else delete own.enabled;
            if (Object.keys(own).length) out[kind] = own;
          }
          if (Object.keys(out).length) room.alerts = out;
          else delete room.alerts;
        },
        (s) => (s.type === "expandable" ? s.title : this._label("alert", s.name))
      )
    );
    return card;
  }

  _effectiveControl(room, section) {
    const defaults = this._config.defaults.control[section] || {};
    const global = this._draft.control?.[section] || {};
    const own = room.control?.[section] || {};
    return { ...defaults, ...global, ...own };
  }

  _defaultHelp(schema, defaults) {
    if (schema.type === "expandable" || schema.name === "entity_id" || schema.name === "mode_select") return undefined;
    const value = defaults[schema.name];
    if (value === undefined || value === null || value === "") return undefined;
    return this._t("default_value", { value: typeof value === "boolean" ? this._t(value ? "enabled" : "disabled") : value });
  }

  _deviceLabel(section, name) {
    if (name === "entity_id") return this._t(section === "fans" ? "fan" : "purifier");
    const map = { mode_select: "purifier_mode_select", open_mode: "purifier_open_mode", closed_mode: "purifier_closed_mode" };
    if (map[name]) return this._label("room", map[name], "overrides");
    return this._label("control", name, section);
  }

  _climateSchema(entityId) {
    return [
      { name: "entity_id", selector: entity("climate") },
      ...(entityId
        ? [
            {
              type: "expandable",
              name: "",
              flatten: true,
              title: this._t("device_settings"),
              schema: [
                { name: "cool_above", selector: num("°C") },
                { name: "off_below", selector: num("°C") },
                { name: "setpoint", selector: num("°C", { step: 0.5 }) },
                { name: "fan_mode", selector: this._choice(this._attr(entityId, "fan_modes")) },
                { name: "closed_for", selector: minutes() },
                { name: "off_on_open", selector: minutes() },
              ],
            },
          ]
        : []),
    ];
  }

  _fanSchema(entityId) {
    const presets = this._attr(entityId, "preset_modes");
    return [
      { name: "entity_id", selector: entity("fan") },
      ...(entityId
        ? [
            {
              type: "expandable",
              name: "",
              flatten: true,
              title: this._t("device_settings"),
              schema: [
                { name: "on_above", selector: num("°C") },
                { name: "off_below", selector: num("°C") },
                { name: "percentage", selector: percent },
                { name: "preset", selector: this._choice(presets) },
                { name: "open_percentage", selector: percent },
                { name: "open_preset", selector: this._choice(presets) },
                { name: "off_preset", selector: this._choice(presets) },
              ],
            },
          ]
        : []),
    ];
  }

  _purifierSchema(item) {
    const entityId = item?.entity_id;
    const presets = this._attr(entityId, "preset_modes");
    const modes = item?.mode_select ? this._attr(item.mode_select, "options") : [];
    return [
      { name: "entity_id", selector: entity("fan") },
      ...(entityId
        ? [
            {
              type: "expandable",
              name: "",
              flatten: true,
              title: this._t("device_settings"),
              schema: [
                { name: "open_percentage", selector: percent },
                { name: "open_preset", selector: this._choice(presets) },
                { name: "closed_preset", selector: this._choice(presets) },
                { name: "mode_select", selector: entity("select") },
                ...(item?.mode_select
                  ? [
                      { name: "open_mode", selector: this._choice(modes) },
                      { name: "closed_mode", selector: this._choice(modes) },
                    ]
                  : []),
                { name: "keep_on", selector: bool },
              ],
            },
          ]
        : []),
    ];
  }
}

const STYLE = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    height: var(--header-height, 56px);
    padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, #fff);
    border-bottom: var(--app-header-border-bottom, none);
    box-sizing: border-box;
    position: sticky;
    top: 0;
    z-index: 2;
  }
  .title { flex: 1; font-size: 20px; font-weight: 400; margin-left: 8px; }
  .actions { display: flex; align-items: center; gap: 8px; }
  .dirty { font-size: 13px; opacity: 0.85; margin-right: 4px; }
  .tabs {
    display: flex;
    gap: 4px;
    padding: 0 12px;
    overflow-x: auto;
    background: var(--app-header-background-color, var(--primary-color));
    position: sticky;
    top: var(--header-height, 56px);
    z-index: 2;
  }
  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--app-header-text-color, #fff);
    opacity: 0.75;
    padding: 12px 14px;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
    white-space: nowrap;
  }
  .tab.active { opacity: 1; border-bottom-color: var(--app-header-text-color, #fff); }
  .content { max-width: 1040px; margin: 0 auto; padding: 16px; display: flex; flex-direction: column; gap: 16px; }
  .card {
    background: var(--ha-card-background, var(--card-background-color, #fff));
    border-radius: var(--ha-card-border-radius, 12px);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color));
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 16px;
  }
  .card-header { display: flex; align-items: center; gap: 10px; font-size: 18px; margin-bottom: 12px; }
  .card-header > ha-icon { color: var(--primary-color); }
  .card-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--divider-color); }
  .btn {
    font: inherit;
    font-size: 14px;
    font-weight: 500;
    padding: 8px 14px;
    border-radius: 18px;
    border: 1px solid var(--divider-color);
    background: transparent;
    color: var(--primary-color);
    cursor: pointer;
  }
  .toolbar .btn { color: var(--app-header-text-color, #fff); border-color: currentColor; }
  .toolbar .btn.primary { background: rgba(255, 255, 255, 0.15); }
  .btn:hover { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08); }
  .btn:disabled { opacity: 0.6; cursor: default; }
  .btn.add { align-self: flex-start; }
  .btn.small { margin-top: 4px; padding: 6px 12px; font-size: 13px; }
  .icon-btn {
    background: none;
    border: none;
    color: var(--secondary-text-color);
    cursor: pointer;
    padding: 6px;
    border-radius: 50%;
    display: inline-flex;
  }
  .icon-btn:hover { background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06); color: var(--primary-color); }
  .banner { padding: 12px 16px; border-radius: 10px; font-size: 14px; line-height: 1.4; }
  .banner.info { background: rgba(var(--rgb-info-color, 3, 155, 229), 0.12); }
  .banner.error { background: rgba(var(--rgb-error-color, 219, 68, 55), 0.14); color: var(--error-color); }
  .banner.success { background: rgba(var(--rgb-success-color, 67, 160, 71), 0.14); }
  .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
  .tile {
    font: inherit;
    text-align: left;
    color: inherit;
    background: var(--ha-card-background, var(--card-background-color, #fff));
    border: 1px solid var(--divider-color);
    border-radius: 12px;
    padding: 14px;
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: 12px;
    align-items: center;
  }
  button.tile { cursor: pointer; }
  .tile ha-icon { grid-row: span 2; color: var(--primary-color); --mdc-icon-size: 28px; }
  .tile.off ha-icon { color: var(--disabled-text-color, var(--secondary-text-color)); }
  .tile-value { font-size: 22px; font-weight: 500; }
  .tile-value:empty { display: none; }
  .tile-label { font-size: 13px; color: var(--secondary-text-color); }
  .alert { display: flex; align-items: flex-start; gap: 12px; padding: 10px 0; border-top: 1px solid var(--divider-color); }
  .alert:first-of-type { border-top: none; }
  .alert .kind { color: var(--warning-color, #ffa600); margin-top: 2px; }
  .alert .kind.too_cold, .alert .kind.window_open_cold { color: var(--info-color, #039be5); }
  .alert .kind.co2_high, .alert .kind.humidity_high, .alert .kind.ventilate { color: var(--primary-color); }
  .alert .kind.close_windows { color: var(--error-color); }
  .alert-body { flex: 1; min-width: 0; }
  .alert-title { font-weight: 500; }
  .alert-meta { font-size: 13px; color: var(--secondary-text-color); margin-top: 2px; }
  .badges { display: flex; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
  .badge { font-size: 12px; padding: 1px 8px; border-radius: 10px; border: 1px solid var(--divider-color); color: var(--secondary-text-color); }
  .row-actions { display: flex; gap: 2px; }
  .empty { color: var(--secondary-text-color); padding: 8px 0; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
  .grid .card { padding: 14px; }
  .grid .card.has-alert .card-header ha-icon { color: var(--warning-color, #ffa600); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    display: inline-flex; align-items: center; gap: 4px; font-size: 13px;
    padding: 3px 10px 3px 6px; border-radius: 14px; background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.05);
  }
  .chip ha-icon { --mdc-icon-size: 16px; color: var(--secondary-text-color); }
  .room-status { margin-top: 10px; font-size: 14px; }
  .is-ok .room-status { color: var(--success-color, #43a047); }
  .has-alert .room-status { color: var(--warning-color, #ffa600); }
  .devices { margin-top: 10px; border-top: 1px solid var(--divider-color); padding-top: 8px; display: flex; flex-direction: column; gap: 4px; }
  .device { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; }
  .device-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .device-state { color: var(--secondary-text-color); white-space: nowrap; }
  .last-title { font-weight: 500; }
  .last-message { white-space: pre-line; margin-top: 4px; }
  .room-header { justify-content: space-between; margin-bottom: 0; }
  .room-toggle { display: flex; align-items: center; gap: 6px; background: none; border: none; color: inherit; font: inherit; font-size: 18px; cursor: pointer; padding: 0; }
  .room-toggle ha-icon { color: var(--secondary-text-color); }
  .subheader { font-size: 14px; font-weight: 500; color: var(--secondary-text-color); margin: 18px 0 8px; text-transform: uppercase; letter-spacing: 0.04em; }
  .help { font-size: 13px; color: var(--secondary-text-color); margin: -4px 0 8px; }
  .device-item { display: flex; align-items: flex-start; gap: 4px; margin-bottom: 8px; }
  .device-item ha-form { flex: 1; }
  @media (max-width: 600px) {
    .content { padding: 12px; }
    .dirty { display: none; }
  }
`;

if (!customElements.get("smart-comfort-panel")) customElements.define("smart-comfort-panel", SmartComfortPanel);
