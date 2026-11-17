import test from 'node:test';
import assert from 'node:assert/strict';
import {mountDashboard} from '../../frontend/static/js/app.js';
import {createDashboardView} from '../../frontend/static/js/dashboard.js';
import {displayValue, coordinates} from '../../frontend/static/js/format.js';
import {documentFixture, leafletFixture, statusFixture, timersFixture} from './helpers.mjs';

test('missing measurements display a dash while valid zero stays zero', () => {
  assert.equal(displayValue(null), '—');
  assert.equal(displayValue(undefined), '—');
  assert.equal(displayValue(0), 0);
  assert.equal(coordinates({lat: null, lon: 0}), null);
  assert.deepEqual(coordinates({lat: 0, lon: 0}), [0, 0]);
  const root = documentFixture();
  const view = createDashboardView(root);
  const data = statusFixture();
  data.latest.bpm = null;
  view.render(data);
  assert.equal(root.getElementById('bpm').textContent, '—');
  assert.equal(root.getElementById('battery').textContent, '0');
  assert.equal(root.getElementById('current').textContent, '0');
});

test('connection notices preserve no-data and 90-second stale thresholds', () => {
  const root = documentFixture(), view = createDashboardView(root);
  const data = statusFixture();
  data.latest.ts = 910;
  view.render(data);
  assert.equal(root.getElementById('connection').textContent, 'Đã nhận dữ liệu thiết bị');
  data.latest.ts = 909;
  view.render(data);
  assert.match(root.getElementById('connection').textContent, /ngoại tuyến/);
  view.render(statusFixture({latest: null}));
  assert.equal(root.getElementById('connection').textContent, 'Chưa có dữ liệu từ ESP32');
});

test('complete composition renders SOS and measurements even when map library is unavailable', async () => {
  const root = documentFixture(), timers = timersFixture();
  const api = {status: async () => statusFixture(), track: async () => ({points: []})};
  const controller = mountDashboard({root, api, leaflet: null, timers});
  await controller.refresh();
  assert.equal(root.getElementById('bpm').textContent, '72');
  assert.equal(root.getElementById('alerts').children[0].children[0].textContent, 'Nhấn nút SOS');
  assert.match(root.getElementById('map').textContent, /Bản đồ chưa tải được/);
  assert.equal([...timers.intervals.values()][0].milliseconds, 5000);
  controller.stop();
  assert.equal(timers.intervals.size, 0);
});

test('overlapping polling shares one pending request', async () => {
  const root = documentFixture(), timers = timersFixture();
  let resolveStatus, requests = 0;
  const api = {status: () => { requests++; return new Promise(resolve => { resolveStatus = resolve; }); }, track: async () => ({points: []})};
  const controller = mountDashboard({root, api, leaflet: null, timers});
  const first = controller.refresh(), second = controller.refresh();
  assert.equal(first, second);
  assert.equal(requests, 1);
  resolveStatus(statusFixture());
  await first;
  controller.stop();
});

test('slow GPS history does not block fresh measurements or duplicate the same history request', async () => {
  const root = documentFixture(), timers = timersFixture();
  const data = statusFixture();
  let resolveHistory, historyRequests = 0;
  const api = {
    status: async () => data,
    track: () => { historyRequests++; return new Promise(resolve => { resolveHistory = resolve; }); },
  };
  const controller = mountDashboard({root, api, leaflet: null, timers});
  await controller.refresh();
  data.latest.bpm = 88;
  await controller.refresh();
  assert.equal(root.getElementById('bpm').textContent, '88');
  assert.equal(historyRequests, 1);
  resolveHistory({points: []});
  await Promise.resolve();
  assert.match(root.getElementById('trackingStatus').textContent, /0 điểm GPS/);
  controller.stop();
});

test('locate button uses displayed device, stays disabled during request and refreshes command', async () => {
  const root = documentFixture(), timers = timersFixture();
  const data = statusFixture();
  data.latest.device_id = 'device-02';
  let resolveLocate, requestedDevice;
  const api = {
    status: async () => data,
    track: async () => ({points: []}),
    locate: device => { requestedDevice = device; return new Promise(resolve => { resolveLocate = resolve; }); },
  };
  const controller = mountDashboard({root, api, leaflet: null, timers});
  await controller.refresh();
  const action = root.getElementById('locate').emit('click');
  assert.equal(root.getElementById('locate').disabled, true);
  assert.equal(requestedDevice, 'device-02');
  data.commands = [{device_id: 'device-02', cmd: 'LOCATE'}];
  resolveLocate({ok: true, message: 'Đã xếp lệnh'});
  await action;
  assert.equal(root.getElementById('locate').disabled, false);
  assert.equal(root.getElementById('commandMessage').textContent, 'Đã xếp lệnh');
  assert.equal(root.getElementById('command').textContent, 'LOCATE');
  controller.stop();
});

test('failed commands show errors and restore the button', async () => {
  const root = documentFixture(), timers = timersFixture();
  const api = {status: async () => statusFixture(), track: async () => ({points: []}), locate: async () => { throw new Error('Mất kết nối'); }};
  const controller = mountDashboard({root, api, leaflet: null, timers});
  await controller.refresh();
  await root.getElementById('locate').emit('click');
  assert.equal(root.getElementById('commandMessage').textContent, 'Mất kết nối');
  assert.equal(root.getElementById('locate').disabled, false);
  controller.stop();
});

test('latest packet without GPS keeps the last valid location and only recenters once', async () => {
  const root = documentFixture(), timers = timersFixture(), {leaflet, calls} = leafletFixture();
  const data = statusFixture({last_location: {device_id: 'ngoc-01', lat: 21, lon: 105, ts: 1000}});
  const controller = mountDashboard({root, leaflet, timers, api: {status: async () => data, track: async () => ({points: []})}});
  await controller.refresh();
  data.latest = {...data.latest, lat: null, lon: null, ts: 1010};
  await controller.refresh();
  assert.equal(root.getElementById('position').textContent, 'Tọa độ: 21.000000, 105.000000');
  assert.equal(calls.markers.length, 1);
  assert.deepEqual(calls.views.map(view => view.zoom), [5, 16]);
  await root.getElementById('followGps').emit('click');
  assert.equal(calls.views.at(-1).zoom, 17);
  controller.stop();
});
