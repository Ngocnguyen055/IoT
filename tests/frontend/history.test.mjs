import test from 'node:test';
import assert from 'node:assert/strict';
import {createHistoryController, createHistoryView} from '../../frontend/static/js/history.js';
import {LoginRequiredError} from '../../frontend/static/js/api.js';
import {documentFixture} from './helpers.mjs';

const response = (changes = {}) => ({items: [{id: 90, ts: 1000, device_id: 'ngoc-01', event: 'button', bpm: 0, spo2: null, battery_pct: 0, lat: 0, lon: 0}],
  pagination: {snapshot: 90, has_previous: false, has_next: true, next_before: 52, previous_after: null}, ...changes});
function fixture(alerts) {
  const root = documentFixture('history.html');
  const controller = createHistoryController({api: {alerts}, view: createHistoryView(root)});
  return {root, controller, element: id => root.getElementById(id)};
}

test('history renders stored measurements, zero coordinates and safe device text', async () => {
  const data = response();
  data.items[0].device_id = '<img src=x onerror=alert(1)>';
  const {controller, element} = fixture(async () => data);
  await controller.refresh();
  const cells = element('historyRows').children[0].children;
  assert.equal(cells[1].textContent, 'Nhấn nút SOS');
  assert.equal(cells[2].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(cells[2].children.length, 0);
  assert.equal(cells[3].textContent, '0 BPM');
  assert.equal(cells[4].textContent, '—');
  assert.equal(cells[5].textContent, '0 %');
  assert.equal(cells[6].textContent, '0.00000, 0.00000');
  assert.equal(element('historyPrevious').disabled, true);
  assert.equal(element('historyNext').disabled, false);
});

test('next and previous use server cursors; refresh starts at the newest page', async () => {
  const calls = [];
  const first = response();
  const second = response({pagination: {snapshot: 90, has_previous: true, has_next: false, previous_after: 50, next_before: null}});
  const results = [first, second, first, first];
  const {controller, element} = fixture(async parameters => { calls.push(parameters); return results.shift(); });
  await controller.refresh();
  await element('historyNext').emit('click');
  assert.equal(element('historyPage').textContent, 'Trang 2');
  assert.equal(element('historyNext').disabled, true);
  await element('historyPrevious').emit('click');
  assert.equal(element('historyPage').textContent, 'Trang 1');
  await element('historyRefresh').emit('click');
  assert.deepEqual(calls, [{}, {snapshot: 90, before: 52}, {snapshot: 90, after: 50}, {}]);
});

test('overlapping clicks share one request and failures preserve the current page', async () => {
  let resolve, requests = 0;
  const {controller, element} = fixture(() => {
    requests++;
    return new Promise(done => { resolve = done; });
  });
  const pending = controller.refresh();
  assert.equal(controller.refresh(), pending);
  assert.equal(element('historyRefresh').disabled, true);
  resolve(response());
  await pending;
  assert.equal(requests, 1);
  const next = element('historyNext').emit('click');
  resolve(Promise.reject(new Error('Mất mạng')));
  await next;
  assert.equal(element('historyPage').textContent, 'Trang 1');
  assert.equal(element('historyRows').children.length, 1);
  assert.equal(element('historyNext').disabled, false);
  assert.match(element('historyNotice').textContent, /Mất mạng/);
});

test('empty history disables navigation; login redirects do not display generic errors', async () => {
  const {controller, element} = fixture(async () => response({items: [], pagination: {snapshot: 0, has_previous: false, has_next: false}}));
  await controller.refresh();
  assert.match(element('historyRows').textContent, /Chưa có cảnh báo/);
  assert.equal(element('historyNext').disabled, true);
  assert.equal(element('historyPrevious').disabled, true);
  const expired = fixture(async () => { throw new LoginRequiredError(); });
  await expired.controller.refresh();
  assert.equal(expired.element('historyNotice').className, 'notice');
});
