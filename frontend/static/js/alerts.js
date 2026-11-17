import {formatTime} from './format.js';

const TITLES = {
  button: 'Nhấn nút SOS',
  high_bpm: 'Cảnh báo BPM trên ngưỡng',
  low_spo2: 'Cảnh báo SpO₂ thấp',
  remote: 'Định vị từ website',
};

export const eventTitle = event => TITLES[event] || event;

export function createAlertsView(root) {
  const container = root.getElementById('alerts');
  return {
    render(alerts) {
      container.replaceChildren();
      if (!alerts.length) {
        container.textContent = 'Chưa có cảnh báo hoặc sự kiện.';
        return;
      }
      for (const alert of alerts) {
        const box = root.createElement('div');
        box.className = 'event';
        const title = root.createElement('b');
        title.textContent = eventTitle(alert.event);
        const details = root.createElement('small');
        details.textContent = formatTime(alert.ts) + (alert.lat == null ? ' · Không có GPS fix' : ' · Có tọa độ');
        box.append(title, details);
        container.append(box);
      }
    },
  };
}
