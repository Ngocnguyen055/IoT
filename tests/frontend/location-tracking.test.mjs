import test from 'node:test';
import assert from 'node:assert/strict';
import {createLocationView} from '../../frontend/static/js/location.js';
import {createTracking} from '../../frontend/static/js/tracking.js';
import {createMapView, trackSegments} from '../../frontend/static/js/map.js';
import {documentFixture, leafletFixture, timersFixture} from './helpers.mjs';

test('GPS validity, stale labels, Google Maps and coordinate copying preserve exact zero coordinates', async () => {
  const root = documentFixture(), timers = timersFixture(), positions = [], copied = [];
  const location = createLocationView(root, {setPosition: point => positions.push(point)}, {clipboard: {writeText: async value => copied.push(value)}, timers});
  location.render(null, 1000);
  assert.equal(root.getElementById('copyCoords').disabled, true);
  location.render({lat: 0, lon: 0, ts: 900}, 1000, 'ngoc-01');
  assert.equal(root.getElementById('locationState').textContent, 'Đã có vị trí');
  assert.equal(root.getElementById('googleMaps').hidden, false);
  assert.match(root.getElementById('googleMaps').href, /0\.000000%2C%200\.000000/);
  await root.getElementById('copyCoords').emit('click');
  assert.deepEqual(copied, ['0.000000, 0.000000']);
  assert.equal(root.getElementById('copyCoords').textContent, 'Đã sao chép');
  assert.equal(timers.timeouts[0].milliseconds, 1600);
  timers.timeouts[0].handler();
  assert.equal(root.getElementById('copyCoords').textContent, 'Sao chép tọa độ');
  location.render({lat: 0, lon: 0, ts: 900}, 1301, 'ngoc-01');
  assert.equal(root.getElementById('locationState').textContent, 'Vị trí cũ');
  assert.equal(positions.length, 1);
});

test('clipboard failures display a useful message without crashing', async () => {
  const root = documentFixture();
  const location = createLocationView(root, {setPosition() {}}, {clipboard: undefined, timers: timersFixture()});
  location.render({lat: 21, lon: 105, ts: 1000}, 1000);
  await root.getElementById('copyCoords').emit('click');
  assert.equal(root.getElementById('copyCoords').textContent, 'Không thể sao chép');
});

test('routes break across gaps longer than 120 seconds and reject null coordinates', () => {
  assert.deepEqual(trackSegments([
    {lat: 0, lon: 0, ts: 0}, {lat: 1, lon: 1, ts: 120},
    {lat: 2, lon: 2, ts: 241}, {lat: 3, lon: 3, ts: 242},
    {lat: null, lon: 4, ts: 243},
  ]), [[[0, 0], [1, 1]], [[2, 2], [3, 3]]]);
});

test('map draws segments and a start marker, clears hidden routes and follows only an existing pin', () => {
  const root = documentFixture(), {leaflet, calls} = leafletFixture();
  const map = createMapView(root, leaflet);
  assert.equal(map.follow(), false);
  const points = [{lat: 21, lon: 105, ts: 0}, {lat: 21.1, lon: 105.1, ts: 15}];
  map.renderTrack(points, true);
  assert.equal(calls.lines.length, 1);
  assert.deepEqual(calls.circles[0], [21, 105]);
  map.renderTrack(points, false);
  assert.equal(calls.clears, 2);
  map.setPosition(points[0]);
  map.setPosition(points[1]);
  assert.equal(map.follow(), true);
  assert.deepEqual(calls.views.at(-1), {position: [21.1, 105.1], zoom: 17});
});

test('latest history selection wins when older requests finish later', async () => {
  const root = documentFixture(), requests = [], rendered = [];
  const api = {track: (device, hours) => new Promise(resolve => requests.push({device, hours, resolve}))};
  const tracking = createTracking(root, api, {renderTrack: (...args) => rendered.push(args), follow: () => false});
  const older = tracking.refresh('ngoc-01');
  root.getElementById('trackHours').value = '1';
  const newer = tracking.refresh('ngoc-01', true);
  requests[1].resolve({points: [{id: 2, lat: 21, lon: 105, ts: 1000}]});
  await newer;
  requests[0].resolve({points: []});
  await older;
  assert.equal(rendered.length, 1);
  assert.equal(rendered[0][0][0].id, 2);
  assert.match(root.getElementById('trackingStatus').textContent, /\(1 giờ\)/);
});

test('history range and visibility controls refetch and preserve the 1000-point notice', async () => {
  const root = documentFixture(), rendered = [], ranges = [];
  const points = Array.from({length: 1000}, (_, id) => ({id, ts: 1000, lat: 21, lon: 105}));
  const tracking = createTracking(root, {track: async (device, hours) => { ranges.push(hours); return {points}; }}, {
    renderTrack: (data, shown) => rendered.push(shown), follow: () => false,
  });
  await tracking.refresh('ngoc-01');
  assert.match(root.getElementById('trackingStatus').textContent, /Đã giới hạn 1000 điểm/);
  root.getElementById('showTrack').checked = false;
  await root.getElementById('showTrack').emit('change');
  root.getElementById('trackHours').value = '6';
  await root.getElementById('trackHours').emit('change');
  assert.deepEqual(rendered, [true, false, false]);
  assert.deepEqual(ranges, [24, 24, 6]);
  await root.getElementById('followGps').emit('click');
  assert.match(root.getElementById('trackingStatus').textContent, /Chưa có vị trí GPS/);
});
