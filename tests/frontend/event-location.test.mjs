import test from 'node:test';
import assert from 'node:assert/strict';
import {createAlertsView} from '../../frontend/static/js/alerts.js';
import {createEventLocation} from '../../frontend/static/js/event-location.js';
import {createMapView} from '../../frontend/static/js/map.js';
import {LoginRequiredError} from '../../frontend/static/js/api.js';
import {documentFixture, leafletFixture} from './helpers.mjs';

const event = (changes = {}) => ({id: 12, event: 'button', device_id: 'ngoc-01', ts: 1000, lat: 0, lon: 0, ...changes});

function fixture({api = {}, search = '', withMap = true} = {}) {
  const root = documentFixture(), leaflet = leafletFixture();
  const map = createMapView(root, withMap ? leaflet.leaflet : null);
  const selection = createEventLocation({root, api, map, search});
  return {root, ...leaflet, map, selection, element: id => root.getElementById(id)};
}

test('clicking an alert shows its recorded coordinates without moving them with live GPS', async () => {
  const {root, selection, map, calls, element} = fixture();
  const selected = event({device_id: '<img src=x onerror=alert(1)>'});
  const alerts = createAlertsView(root, {onSelect: item => selection.select(item)});
  alerts.render([selected]);
  const button = element('alerts').children[0];
  assert.equal(button.tagName, 'button');
  await button.emit('click');
  assert.equal(element('eventLocation').hidden, false);
  assert.match(element('eventLocationMessage').textContent, /0\.000000, 0\.000000/);
  assert.match(element('eventGoogleMaps').href, /0\.000000%2C%200\.000000/);
  assert.equal(element('eventGoogleMaps').hidden, false);
  const views = calls.views.length;
  map.setPosition({lat: 21, lon: 105, ts: 2000});
  assert.equal(calls.views.length, views);
  assert.deepEqual(calls.markers[0].position, [21, 105]);
  assert.deepEqual(calls.circleLayers[0].position, [0, 0]);
  const popup = calls.circleLayers[0].popup;
  assert.match(popup.textContent, /<img src=x/);
  assert.equal(popup.children[1].children.length, 0);
  assert.equal(calls.circleLayers[0].popupOpen, true);
});

test('events without GPS explain the missing location and never reuse the latest position', () => {
  const {selection, map, calls, element} = fixture();
  map.setPosition({lat: 21, lon: 105, ts: 2000});
  selection.select(event());
  const selectedPin = calls.circleLayers[0], views = calls.views.length;
  selection.select(event({id: 13, lat: null, lon: null}));
  assert.equal(selectedPin.removed, true);
  assert.equal(calls.circleLayers.length, 1);
  assert.equal(calls.views.length, views);
  assert.match(element('eventLocationMessage').textContent, /Không có tọa độ GPS/);
  assert.equal(element('eventGoogleMaps').hidden, true);
  assert.deepEqual(calls.markers[0].position, [21, 105]);
});

test('history links load a single original event even if it is absent from the home list', async () => {
  const requested = [];
  const {selection, calls, element} = fixture({search: '?event=42', api: {alert: async id => { requested.push(id); return {item: event({id: 42, device_id: 'saved-device-42'})}; }}});
  await selection.openLinked();
  assert.deepEqual(requested, ['42']);
  assert.match(element('eventLocationTime').textContent, /saved-device-42/);
  assert.equal(calls.circleLayers.length, 1);
});

test('closing a pending event or choosing another event prevents a late response replacing it', async () => {
  let resolve;
  const first = fixture({search: '?event=42', api: {alert: () => new Promise(done => { resolve = done; })}});
  const loading = first.selection.openLinked();
  await first.element('closeEventLocation').emit('click');
  resolve({item: event({id: 42})});
  await loading;
  assert.equal(first.element('eventLocation').hidden, true);
  assert.equal(first.calls.circleLayers.length, 0);
  const second = fixture({search: '?event=42', api: {alert: () => new Promise(done => { resolve = done; })}});
  const pending = second.selection.openLinked();
  second.selection.select(event({id: 55, event: 'low_spo2'}));
  resolve({item: event({id: 42})});
  await pending;
  assert.equal(second.element('eventLocationTitle').textContent, 'Cảnh báo SpO₂ thấp');
  assert.equal(second.calls.circleLayers.length, 1);
});

test('lookup failures and malformed links show local errors; authentication redirect stays separate', async () => {
  const failed = fixture({search: '?event=999', api: {alert: async () => { throw new Error('Không tìm thấy sự kiện.'); }}});
  await failed.selection.openLinked();
  assert.match(failed.element('eventLocationMessage').textContent, /Không tìm thấy/);
  assert.equal(failed.element('eventGoogleMaps').hidden, true);
  const invalid = fixture({search: '?event=1e3'});
  await invalid.selection.openLinked();
  assert.match(invalid.element('eventLocationMessage').textContent, /không hợp lệ/);
  const expired = fixture({search: '?event=42', api: {alert: async () => { throw new LoginRequiredError(); }}});
  await expired.selection.openLinked();
  assert.match(expired.element('eventLocationMessage').textContent, /Đang đọc/);
});

test('event coordinates remain available through Google Maps when Leaflet cannot load', () => {
  const {selection, element} = fixture({withMap: false});
  selection.select(event());
  assert.match(element('eventLocationMessage').textContent, /Bản đồ chưa tải được/);
  assert.equal(element('eventGoogleMaps').hidden, false);
});

test('cached older HTML without the event panel does not break the dashboard', async () => {
  const selection = createEventLocation({root: documentFixture('login.html'), api: {}, map: {}, search: '?event=12'});
  selection.select(event());
  await selection.openLinked();
});
