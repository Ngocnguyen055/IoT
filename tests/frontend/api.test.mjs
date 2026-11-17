import test from 'node:test';
import assert from 'node:assert/strict';
import {createApi, LoginRequiredError} from '../../frontend/static/js/api.js';

test('API client keeps endpoint, query encoding, cookies and LOCATE JSON contract', async () => {
  const calls = [];
  const api = createApi({fetchImpl: async (url, options) => {
    calls.push({url, options});
    return {status: 200, ok: true, json: async () => ({ok: true})};
  }});
  await api.status();
  await api.track('device / one', 24);
  await api.locate('device / one');
  assert.equal(calls[0].url, '/api/dashboard');
  assert.equal(calls[1].url, '/api/track?device_id=device%20%2F%20one&hours=24');
  assert.equal(calls[2].url, '/api/command');
  assert.equal(calls[2].options.method, 'POST');
  assert.deepEqual(JSON.parse(calls[2].options.body), {device_id: 'device / one', command: 'LOCATE'});
  for (const {options} of calls) {
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
  }
});

test('401 on any API redirects once and returns a distinct authentication error', async () => {
  let redirects = 0;
  const api = createApi({fetchImpl: async () => ({status: 401}), onUnauthorized: () => { redirects++; }});
  for (const request of [() => api.status(), () => api.alerts(), () => api.track('ngoc-01', 24), () => api.locate('ngoc-01')]) {
    await assert.rejects(request, LoginRequiredError);
  }
  assert.equal(redirects, 1);
});

test('alert history includes only supplied cursors and preserves an empty snapshot', async () => {
  const calls = [];
  const api = createApi({fetchImpl: async url => {
    calls.push(url);
    return {status: 200, ok: true, json: async () => ({})};
  }});
  await api.alerts();
  await api.alerts({snapshot: 0});
  await api.alerts({snapshot: 92, before: 51, after: null});
  await api.alerts({snapshot: 92, after: 31});
  assert.deepEqual(calls, ['/api/alerts', '/api/alerts?snapshot=0', '/api/alerts?snapshot=92&before=51', '/api/alerts?snapshot=92&after=31']);
});

test('API errors keep server messages and handle non-JSON gateway responses', async () => {
  const api = createApi({fetchImpl: async () => ({status: 400, ok: false, json: async () => ({error: 'bad command'})})});
  await assert.rejects(() => api.locate('ngoc-01'), /bad command/);
  const gateway = createApi({fetchImpl: async () => ({status: 502, ok: false, json: async () => { throw new Error('HTML'); }})});
  await assert.rejects(() => gateway.status(), /Không thể đọc API/);
});
