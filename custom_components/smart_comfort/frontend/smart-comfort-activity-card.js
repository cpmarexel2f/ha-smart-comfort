/**
 * Smart Comfort activity card: what Smart Comfort did and why, live.
 * Also used by the Activity tab of the Smart Comfort panel (with filters and days).
 *
 * type: custom:smart-comfort-activity-card
 * title: Smart Comfort      # optional
 * limit: 10                 # entries shown
 * kinds: [device, lighting] # optional: only these (device, lighting, presence, display, notified, manual, reset, failed)
 * room: Séjour              # optional: only this room
 */

const STRINGS = {
  en: {
    title: "Smart Comfort activity",
    empty: "Nothing yet.",
    not_loaded: "Smart Comfort is not loaded.",
    all: "All",
    group_devices: "Devices",
    group_lights: "Lights",
    group_notifications: "Notifications",
    group_manual: "By hand",
    today: "Today",
    yesterday: "Yesterday",
    t_cool: "Cooling",
    t_cool_night: "Cooling, quiet night",
    t_off: "Off",
    t_off_open: "Off: a window stays open",
    t_on: "On: warm",
    t_on_night: "On, quiet night",
    t_boost: "Window boost",
    t_normal: "Back to normal",
    t_night: "Night mode",
    t_keep_on: "Turned back on",
    lighting: "Brightness of the moment",
    presence_on: "On: someone came in",
    presence_off: "Off: nobody left",
    display_off: "Indicator off",
    display_on: "Indicator back on",
    notified: "Notification",
    cleared: "Notification cleared: everything is back to normal",
    manual: "Changed by hand: left alone",
    manual_until: "Changed by hand: left alone until {time}",
    reset: "Back to normal (set time)",
    failed: "Could not be sent",
    f_title: "Title",
    f_limit: "Entries",
    f_kinds: "Only",
    f_room: "Room",
  },
  fr: {
    title: "Activité Smart Comfort",
    empty: "Rien pour l'instant.",
    not_loaded: "Smart Comfort n'est pas chargé.",
    all: "Tout",
    group_devices: "Appareils",
    group_lights: "Lumières",
    group_notifications: "Notifications",
    group_manual: "À la main",
    today: "Aujourd'hui",
    yesterday: "Hier",
    t_cool: "Refroidit",
    t_cool_night: "Refroidit, nuit calme",
    t_off: "Éteint",
    t_off_open: "Éteint : une fenêtre reste ouverte",
    t_on: "Allumé : il fait chaud",
    t_on_night: "Allumé, nuit calme",
    t_boost: "Boost fenêtre",
    t_normal: "Retour à la normale",
    t_night: "Mode nuit",
    t_keep_on: "Rallumé",
    lighting: "Intensité du moment",
    presence_on: "Allumée : quelqu'un est entré",
    presence_off: "Éteinte : plus personne",
    display_off: "Voyant éteint",
    display_on: "Voyant rallumé",
    notified: "Notification",
    cleared: "Notification effacée : tout est revenu à la normale",
    manual: "Changé à la main : laissé tel quel",
    manual_until: "Changé à la main : laissé tel quel jusqu'à {time}",
    reset: "Retour à la normale (heure fixe)",
    failed: "Commande non envoyée",
    f_title: "Titre",
    f_limit: "Entrées",
    f_kinds: "Seulement",
    f_room: "Pièce",
  },
  de: {
    title: "Smart Comfort Aktivität",
    empty: "Noch nichts.",
    not_loaded: "Smart Comfort ist nicht geladen.",
    all: "Alle",
    group_devices: "Geräte",
    group_lights: "Lichter",
    group_notifications: "Benachrichtigungen",
    group_manual: "Von Hand",
    today: "Heute",
    yesterday: "Gestern",
    t_cool: "Kühlt",
    t_cool_night: "Kühlt, Nachtruhe",
    t_off: "Aus",
    t_off_open: "Aus: ein Fenster bleibt offen",
    t_on: "An: warm",
    t_on_night: "An, Nachtruhe",
    t_boost: "Fenster-Boost",
    t_normal: "Zurück zum Normalzustand",
    t_night: "Nachtmodus",
    t_keep_on: "Wieder eingeschaltet",
    lighting: "Helligkeit des Moments",
    presence_on: "An: jemand ist gekommen",
    presence_off: "Aus: niemand mehr da",
    display_off: "Anzeige aus",
    display_on: "Anzeige wieder an",
    notified: "Benachrichtigung",
    cleared: "Benachrichtigung gelöscht: alles wieder normal",
    manual: "Von Hand geändert: in Ruhe gelassen",
    manual_until: "Von Hand geändert: in Ruhe gelassen bis {time}",
    reset: "Zurück zum Normalzustand (feste Uhrzeit)",
    failed: "Konnte nicht gesendet werden",
    f_title: "Titel",
    f_limit: "Einträge",
    f_kinds: "Nur",
    f_room: "Raum",
  },
  es: {
    title: "Actividad de Smart Comfort",
    empty: "Nada por ahora.",
    not_loaded: "Smart Comfort no está cargado.",
    all: "Todo",
    group_devices: "Aparatos",
    group_lights: "Luces",
    group_notifications: "Notificaciones",
    group_manual: "A mano",
    today: "Hoy",
    yesterday: "Ayer",
    t_cool: "Enfriando",
    t_cool_night: "Enfriando, noche tranquila",
    t_off: "Apagado",
    t_off_open: "Apagado: una ventana sigue abierta",
    t_on: "Encendido: hace calor",
    t_on_night: "Encendido, noche tranquila",
    t_boost: "Refuerzo por ventana",
    t_normal: "Vuelta a lo normal",
    t_night: "Modo noche",
    t_keep_on: "Encendido de nuevo",
    lighting: "Brillo del momento",
    presence_on: "Encendida: alguien ha entrado",
    presence_off: "Apagada: ya no hay nadie",
    display_off: "Indicador apagado",
    display_on: "Indicador encendido",
    notified: "Notificación",
    cleared: "Notificación borrada: todo ha vuelto a la normalidad",
    manual: "Cambiado a mano: se deja así",
    manual_until: "Cambiado a mano: se deja así hasta las {time}",
    reset: "Vuelta a lo normal (hora fija)",
    failed: "No se pudo enviar",
    f_title: "Título",
    f_limit: "Entradas",
    f_kinds: "Solo",
    f_room: "Habitación",
  },
};

const ICONS = {
  device: "mdi:fan",
  lighting: "mdi:lightbulb-auto-outline",
  presence_on: "mdi:motion-sensor",
  presence_off: "mdi:motion-sensor-off",
  display: "mdi:led-off",
  notified: "mdi:bell-ring-outline",
  cleared: "mdi:bell-check-outline",
  manual: "mdi:hand-back-right-outline",
  reset: "mdi:clock-check-outline",
  failed: "mdi:alert-circle-outline",
};
const DEVICE_ICONS = { climate: "mdi:air-conditioner", fan: "mdi:fan" };
// Filter groups of the Activity tab, and the kinds of the card option.
const GROUPS = {
  devices: ["device", "display", "reset", "failed"],
  lights: ["lighting", "presence_on", "presence_off"],
  notifications: ["notified", "cleared"],
  manual: ["manual"],
};
const KIND_OPTIONS = ["device", "lighting", "presence", "display", "notified", "manual", "reset", "failed"];

function matches(entry, config) {
  if (config.room && entry.room !== config.room) return false;
  const kinds = config.kinds;
  if (!kinds?.length) return true;
  return kinds.some((k) => k === entry.kind || (k === "presence" && entry.kind.startsWith("presence")) || (k === "notified" && entry.kind === "cleared"));
}

class SmartComfortActivityCard extends HTMLElement {
  static getStubConfig() {
    return { limit: 10 };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "limit", selector: { number: { min: 1, max: 100, mode: "box" } } },
        {
          name: "kinds",
          selector: { select: { multiple: true, mode: "list", options: KIND_OPTIONS } },
        },
        { name: "room", selector: { text: {} } },
      ],
      computeLabel: (schema) => {
        const lang = (document.querySelector("home-assistant")?.hass?.language || "en").split("-")[0];
        return (STRINGS[lang] || STRINGS.en)[`f_${schema.name}`] || schema.name;
      },
    };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entries = [];
    this._group = "all";
    this._loaded = true;
  }

  setConfig(config) {
    this._config = { limit: 10, ...config };
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._subscribe();
    else if (!this._rendered) this._render();
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._subscribe();
  }

  disconnectedCallback() {
    this._unsubscribe();
  }

  getCardSize() {
    return Math.min(8, 1 + (this._config?.limit || 10));
  }

  _t(key, values = {}) {
    const lang = (this._hass?.language || "en").split("-")[0];
    const text = (STRINGS[lang] || STRINGS.en)[key] ?? STRINGS.en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, k) => values[k] ?? "");
  }

  async _subscribe() {
    this._unsubscribe();
    const limit = this._config?.panel ? 300 : Math.max(50, (this._config?.limit || 10) * 5);
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (msg) => {
          if (msg.entries) this._entries = msg.entries;
          if (msg.added) this._entries = [...[...msg.added].reverse(), ...this._entries].slice(0, 300);
          this._loaded = true;
          this._render();
        },
        { type: "smart_comfort/activity", limit }
      );
    } catch (_err) {
      this._loaded = false;
      this._render();
    }
  }

  _unsubscribe() {
    if (this._unsub) {
      this._unsub();
      this._unsub = undefined;
    }
  }

  _name(entityId) {
    return this._hass?.states[entityId]?.attributes.friendly_name || entityId;
  }

  _time(iso, withDay = false) {
    const date = new Date(iso);
    const options = { hour: "2-digit", minute: "2-digit" };
    if (withDay) Object.assign(options, { day: "numeric", month: "short" });
    return date.toLocaleString(this._hass?.language, options);
  }

  _day(iso) {
    const date = new Date(iso);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return this._t("today");
    if (date.toDateString() === yesterday.toDateString()) return this._t("yesterday");
    return date.toLocaleDateString(this._hass?.language, { weekday: "long", day: "numeric", month: "long" });
  }

  /** What happened, in a few words, and the icon. */
  _describe(entry) {
    const data = entry.data || {};
    const pct = data.brightness_pct ?? data.value;
    let text;
    let icon = ICONS[entry.kind] || "mdi:information-outline";
    switch (entry.kind) {
      case "device":
        text = this._t(`t_${entry.target}`);
        icon = DEVICE_ICONS[(entry.entity_id || "").split(".")[0]] || icon;
        if (data.preset_mode) text += ` · ${data.preset_mode}`;
        else if (data.option) text += ` · ${data.option}`;
        else if (data.fan_mode) text += ` · ${data.fan_mode}`;
        break;
      case "lighting":
      case "presence_on":
        text = this._t(entry.kind) + (pct !== undefined ? ` · ${pct} %` : "");
        break;
      case "display":
        text = this._t(entry.target === "display_on" ? "display_on" : "display_off");
        if (entry.target === "display_on") icon = "mdi:led-on";
        break;
      case "notified":
        return { icon, text: entry.title || this._t("notified"), detail: entry.message, severity: entry.severity };
      case "manual":
        text = entry.until ? this._t("manual_until", { time: this._time(entry.until) }) : this._t("manual");
        break;
      case "failed":
        text = `${this._t("failed")}${entry.target ? ` · ${this._t(`t_${entry.target}`)}` : ""}`;
        break;
      default:
        text = this._t(entry.kind);
    }
    return { icon, text };
  }

  _visible() {
    const config = this._config || {};
    let entries = this._entries.filter((e) => matches(e, config));
    if (config.panel && this._group !== "all") entries = entries.filter((e) => GROUPS[this._group].includes(e.kind));
    return config.panel ? entries : entries.slice(0, config.limit || 10);
  }

  _render() {
    if (!this._config) return;
    this._rendered = Boolean(this._hass);
    const root = this.shadowRoot;
    root.innerHTML = `<style>${STYLE}</style>`;
    const card = document.createElement(this._config.panel ? "div" : "ha-card");
    if (!this._config.panel) card.header = this._config.title ?? this._t("title");
    root.append(card);
    const body = document.createElement("div");
    body.className = this._config.panel ? "body flat" : "body";
    card.append(body);
    if (this._config.panel) body.append(this._chips());
    if (!this._loaded) {
      body.append(this._el("div", "empty", this._t("not_loaded")));
      return;
    }
    const entries = this._visible();
    if (!entries.length) {
      body.append(this._el("div", "empty", this._t("empty")));
      return;
    }
    let day = null;
    for (const entry of entries) {
      const thisDay = this._day(entry.at);
      if (this._config.panel && thisDay !== day) {
        body.append(this._el("div", "day", thisDay));
        day = thisDay;
      }
      body.append(this._row(entry));
    }
  }

  _chips() {
    const chips = this._el("div", "chips");
    for (const group of ["all", ...Object.keys(GROUPS)]) {
      const chip = this._el("button", `chip${group === this._group ? " active" : ""}`, this._t(group === "all" ? "all" : `group_${group}`));
      chip.addEventListener("click", () => {
        this._group = group;
        this._render();
      });
      chips.append(chip);
    }
    return chips;
  }

  _row(entry) {
    const { icon, text, detail, severity } = this._describe(entry);
    const row = this._el("div", `row ${entry.kind}${severity ? ` ${severity}` : ""}`);
    const badge = this._el("div", "badge");
    const i = document.createElement("ha-icon");
    i.icon = icon;
    badge.append(i);
    const main = this._el("div", "main");
    const who = entry.entity_id ? this._name(entry.entity_id) : null;
    main.append(this._el("div", "what", who ? `${who} — ${text}` : text));
    if (detail) main.append(this._el("div", "detail", detail));
    const meta = [entry.room, this._time(entry.at, !this._config.panel && this._day(entry.at) !== this._t("today"))];
    main.append(this._el("div", "meta", meta.filter(Boolean).join(" · ")));
    row.append(badge, main);
    if (entry.entity_id) {
      row.classList.add("clickable");
      row.addEventListener("click", () => {
        const event = new Event("hass-more-info", { bubbles: true, composed: true });
        event.detail = { entityId: entry.entity_id };
        this.dispatchEvent(event);
      });
    }
    return row;
  }

  _el(tag, cls, text) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
  }
}

const STYLE = `
  :host { display: block; }
  .body { padding: 0 16px 12px; }
  .body.flat { padding: 0; }
  .empty { color: var(--secondary-text-color); padding: 12px 0; }
  .day { margin: 14px 0 4px; font-size: 13px; font-weight: 500; text-transform: capitalize; color: var(--secondary-text-color); }
  .row { display: flex; gap: 12px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid var(--divider-color); }
  .row:last-child { border-bottom: none; }
  .row.clickable { cursor: pointer; }
  .badge { flex: none; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12); color: var(--primary-color); --mdc-icon-size: 20px; }
  .row.lighting .badge, .row.presence_on .badge, .row.presence_off .badge { background: rgba(255, 166, 0, 0.14); color: var(--warning-color, #ffa600); }
  .row.notified .badge, .row.cleared .badge { background: rgba(var(--rgb-info-color, 3, 155, 229), 0.12); color: var(--info-color, #039be5); }
  .row.notified.warning .badge { background: rgba(255, 166, 0, 0.14); color: var(--warning-color, #ffa600); }
  .row.notified.critical .badge, .row.failed .badge { background: rgba(219, 68, 55, 0.12); color: var(--error-color, #db4437); }
  .row.manual .badge, .row.display .badge { background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06); color: var(--secondary-text-color); }
  .main { min-width: 0; flex: 1; }
  .what { font-size: 14px; line-height: 20px; }
  .detail { font-size: 13px; color: var(--secondary-text-color); white-space: pre-line; margin-top: 2px; }
  .meta { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 0 4px; }
  .chip { border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); border-radius: 16px;
    padding: 6px 12px; font: inherit; font-size: 13px; cursor: pointer; }
  .chip.active { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
`;

if (!customElements.get("smart-comfort-activity-card")) {
  customElements.define("smart-comfort-activity-card", SmartComfortActivityCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "smart-comfort-activity-card",
    name: "Smart Comfort activity",
    description: "What Smart Comfort did and why, live: devices, lights, notifications, changes by hand.",
    preview: false,
  });
}
