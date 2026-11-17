import {LoginRequiredError} from './api.js';
import {DEFAULT_DEVICE, OFFLINE_AFTER_SECONDS, POLL_INTERVAL_MS} from './config.js';
import {displayValue, formatTime} from './format.js';

export function createDashboardView(root) {
  const element = id => root.getElementById(id);
  return {
    render(data) {
      const latest = data.latest;
      element('connection').textContent = !latest ? 'Chưa có dữ liệu từ ESP32'
        : data.now - latest.ts > OFFLINE_AFTER_SECONDS ? 'Thiết bị có thể đang ngoại tuyến — dữ liệu cuối đã cũ' : 'Đã nhận dữ liệu thiết bị';
      if (latest) {
        const fields = {bpm: 'bpm', spo2: 'spo2', battery: 'battery_pct', voltage: 'battery_voltage', sat: 'gps_satellites', current: 'current_ma'};
        for (const [id, field] of Object.entries(fields)) element(id).textContent = displayValue(latest[field]);
        element('device').textContent = latest.device_id;
        element('time').textContent = formatTime(latest.ts);
      }
      const device = latest?.device_id || data.last_location?.device_id || DEFAULT_DEVICE;
      element('command').textContent = (data.commands.find(command => command.device_id === device) || {}).cmd || 'NONE';
      return device;
    },
    error: error => { element('connection').textContent = 'Lỗi tải dữ liệu: ' + error.message; },
    onLocate: handler => element('locate').addEventListener('click', handler),
    locateBusy: busy => { element('locate').disabled = busy; },
    commandMessage: message => { element('commandMessage').textContent = message; },
  };
}

export function createDashboardController({api, view, alerts, location, tracking, timers = globalThis}) {
  let device = DEFAULT_DEVICE, pendingRefresh = null, interval = null;

  function refresh() {
    if (pendingRefresh) return pendingRefresh;
    pendingRefresh = (async () => {
      try {
        const data = await api.status();
        device = view.render(data);
        location.render(data.last_location, data.now, data.last_location?.device_id || data.latest?.device_id);
        alerts.render(data.alerts);
        void tracking.refresh(device);
      } catch (error) {
        if (!(error instanceof LoginRequiredError)) view.error(error);
      }
    })().finally(() => { pendingRefresh = null; });
    return pendingRefresh;
  }

  async function locate() {
    view.locateBusy(true);
    try {
      const data = await api.locate(device);
      view.commandMessage(data.message || data.error);
    } catch (error) {
      if (!(error instanceof LoginRequiredError)) view.commandMessage(error.message);
    } finally {
      view.locateBusy(false);
      await refresh();
    }
  }

  view.onLocate(locate);
  return {
    refresh,
    start() {
      if (interval !== null) return;
      void refresh();
      interval = timers.setInterval(refresh, POLL_INTERVAL_MS);
    },
    stop() {
      if (interval !== null) timers.clearInterval(interval);
      interval = null;
    },
  };
}
