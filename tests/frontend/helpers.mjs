import {readFileSync} from 'node:fs';

class Element {
  constructor(tag = 'div') {
    this.tagName = tag;
    this.children = [];
    this.events = new Map();
    this.value = '';
    this.checked = false;
    this.disabled = false;
    this.hidden = false;
    this.className = '';
    this._text = '';
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ''; this.children = [...children]; }
  addEventListener(name, handler) {
    const handlers = this.events.get(name) || [];
    handlers.push(handler);
    this.events.set(name, handlers);
  }
  async emit(name) {
    for (const handler of this.events.get(name) || []) await handler({target: this});
  }
}

export function documentFixture() {
  const html = readFileSync(new URL('../../frontend/templates/index.html', import.meta.url), 'utf8');
  const elements = new Map();
  for (const match of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>([^<]*)/g)) {
    const element = new Element(match[1]);
    element.textContent = match[4].trim();
    element.disabled = /\bdisabled\b/.test(match[2]);
    element.hidden = /\bhidden\b/.test(match[2]);
    element.checked = /\bchecked\b/.test(match[2]);
    elements.set(match[3], element);
  }
  elements.get('trackHours').value = '24';
  return {getElementById: id => elements.get(id) || null, createElement: tag => new Element(tag)};
}

export function timersFixture() {
  const intervals = new Map(), timeouts = [];
  let nextId = 0;
  return {
    intervals, timeouts,
    setInterval(handler, milliseconds) { intervals.set(++nextId, {handler, milliseconds}); return nextId; },
    clearInterval(id) { intervals.delete(id); },
    setTimeout(handler, milliseconds) { timeouts.push({handler, milliseconds}); return timeouts.length; },
  };
}

export function leafletFixture() {
  const calls = {views: [], markers: [], lines: [], circles: [], clears: 0};
  const map = {setView(position, zoom) { calls.views.push({position, zoom}); return this; }};
  const layers = {addTo() { return this; }, clearLayers() { calls.clears++; }};
  const layer = () => ({addTo() { return this; }, bindPopup() { return this; }});
  return {
    calls,
    leaflet: {
      map: () => map,
      tileLayer: layer,
      layerGroup: () => layers,
      marker(position) {
        const marker = {...layer(), position, setLatLng(value) { this.position = value; return this; }, getLatLng() { return this.position; }};
        calls.markers.push(marker);
        return marker;
      },
      polyline(points) { calls.lines.push(points); return layer(); },
      circleMarker(position) { calls.circles.push(position); return layer(); },
    },
  };
}

export function statusFixture(changes = {}) {
  return {
    now: 1000,
    latest: {device_id: 'ngoc-01', ts: 1000, bpm: 72, spo2: 98, battery_pct: 0, battery_voltage: 4.004, gps_satellites: 0, current_ma: 0},
    last_location: null,
    alerts: [{event: 'button', ts: 1000, lat: null}],
    commands: [],
    ...changes,
  };
}
