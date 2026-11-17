import {LoginRequiredError} from './api.js';
import {DEFAULT_DEVICE} from './config.js';
import {formatTime} from './format.js';

export function createTracking(root, api, map) {
  const element = id => root.getElementById(id);
  let device = DEFAULT_DEVICE, signature = '', requestVersion = 0;
  let pending = null, pendingSelection = null;

  function refresh(nextDevice = device, force = false) {
    device = nextDevice;
    const hours = Number(element('trackHours').value);
    const shown = element('showTrack').checked;
    const selection = `${device}:${hours}:${shown}`;
    if (pending && pendingSelection === selection) return pending;
    const version = ++requestVersion;
    pendingSelection = selection;
    pending = (async () => {
      try {
        const data = await api.track(device, hours);
        if (version !== requestVersion) return;
        const points = data.points || [];
        const first = points[0], last = points[points.length - 1];
        const nextSignature = `${device}:${hours}:${shown}:${points.length}:${first?.id}:${last?.id}`;
        if (force || nextSignature !== signature) {
          signature = nextSignature;
          map.renderTrack(points, shown);
        }
        element('trackingStatus').textContent = `${points.length} điểm GPS (${hours} giờ) · Điểm cuối: ${last ? formatTime(last.ts) : '—'}`
          + (points.length >= 1000 ? ' · Đã giới hạn 1000 điểm' : '');
      } catch (error) {
        if (version === requestVersion && !(error instanceof LoginRequiredError)) {
          element('trackingStatus').textContent = 'Lỗi tải hành trình: ' + error.message;
        }
      }
    })().finally(() => {
      if (version === requestVersion) {
        pending = null;
        pendingSelection = null;
      }
    });
    return pending;
  }

  element('trackHours').addEventListener('change', () => refresh(device, true));
  element('showTrack').addEventListener('change', () => refresh(device, true));
  element('followGps').addEventListener('click', () => {
    if (!map.follow()) element('trackingStatus').textContent = 'Chưa có vị trí GPS hợp lệ để định tâm bản đồ';
  });
  return {refresh};
}
