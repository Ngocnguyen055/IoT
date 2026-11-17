import test from 'node:test';
import assert from 'node:assert/strict';
import {createMapView} from '../../frontend/static/js/map.js';
import {documentFixture, leafletFixture} from './helpers.mjs';

test('default basemap uses the reachable source at its native zoom without forcing cache misses', () => {
  const root = documentFixture(), {leaflet, calls} = leafletFixture();
  createMapView(root, leaflet);
  const background = calls.tiles[0];
  assert.equal(background.url, 'https://tile.openstreetmap.de/{z}/{x}/{y}.png');
  assert.equal(background.options.maxZoom, 18);
  assert.equal(background.options.maxNativeZoom, 18);
  assert.equal(background.options.updateWhenZooming, false);
  assert.match(background.options.attribution, /OpenStreetMap/);
  assert.match(background.options.attribution, /FOSSGIS/);
  assert.equal(background.url.includes('?'), false);
});

test('completed tile requests do not hide failures; manual retry reloads only the background', async () => {
  const root = documentFixture(), {leaflet, calls} = leafletFixture();
  const view = createMapView(root, leaflet);
  view.setPosition({lat: 21, lon: 105, ts: 1000});
  view.renderTrack([{lat: 21, lon: 105, ts: 1000}, {lat: 21.1, lon: 105.1, ts: 1015}], true);
  const background = calls.tiles[0], failedTile = {};
  background.emit('tileerror', {tile: failedTile});
  background.emit('load');
  assert.match(root.getElementById('mapStatus').textContent, /chưa tải được/);
  assert.match(root.getElementById('mapStatus').className, /error/);
  await root.getElementById('reloadMap').emit('click');
  assert.equal(background.redraws, 1);
  assert.match(root.getElementById('mapStatus').textContent, /Đang tải/);
  background.emit('tileload', {tile: {}});
  background.emit('load');
  assert.match(root.getElementById('mapStatus').textContent, /đã tải/);
  assert.equal(calls.markers.length, 1);
  assert.equal(calls.clears, 1);
  assert.equal(calls.lines.length, 1);
});

test('switching sources preserves position and track; removed tiles no longer report failures', async () => {
  const root = documentFixture(), {leaflet, calls} = leafletFixture();
  const view = createMapView(root, leaflet);
  view.setPosition({lat: 21, lon: 105, ts: 1000});
  const first = calls.tiles[0];
  root.getElementById('basemapSource').value = 'osm';
  await root.getElementById('basemapSource').emit('change');
  assert.equal(first.removed, true);
  assert.equal(calls.tiles.length, 2);
  assert.equal(calls.tiles[1].url, 'https://tile.openstreetmap.org/{z}/{x}/{y}.png');
  assert.equal(calls.maxZooms.at(-1), 19);
  first.emit('tileerror', {tile: {}});
  assert.doesNotMatch(root.getElementById('mapStatus').className, /error/);
  assert.equal(calls.markers.length, 1);
  assert.equal(calls.clears, 0);
  assert.equal(view.follow(), true);
});

test('failed tiles leaving the buffer clear warnings and container resize updates Leaflet', () => {
  const root = documentFixture(), {leaflet, calls, mapEvents} = leafletFixture();
  let resize, observed, disconnected = false;
  class Observer {
    constructor(callback) { resize = callback; }
    observe(element) { observed = element; }
    disconnect() { disconnected = true; }
  }
  createMapView(root, leaflet, {ResizeObserverImpl: Observer});
  const background = calls.tiles[0], tile = {};
  background.emit('tileerror', {tile});
  background.emit('load');
  background.emit('tileunload', {tile});
  assert.doesNotMatch(root.getElementById('mapStatus').className, /error/);
  assert.equal(observed, root.getElementById('map'));
  resize();
  assert.deepEqual(calls.resizes, [{pan: false, debounceMoveend: true}]);
  mapEvents.get('unload')();
  assert.equal(disconnected, true);
});

test('missing Leaflet shows a distinct library error and disables inactive map controls', () => {
  const root = documentFixture();
  const view = createMapView(root, null);
  assert.match(root.getElementById('mapStatus').textContent, /thư viện bản đồ/);
  assert.equal(root.getElementById('basemapSource').disabled, true);
  assert.equal(root.getElementById('reloadMap').disabled, true);
  assert.equal(view.follow(), false);
});
