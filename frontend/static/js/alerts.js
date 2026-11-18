import {coordinates, formatTime} from './format.js';

const TITLES = {
  button: 'Nhấn nút SOS',
  high_bpm: 'Cảnh báo BPM trên ngưỡng',
  low_spo2: 'Cảnh báo SpO₂ thấp',
  remote: 'Định vị từ website',
};

export const eventTitle = event => TITLES[event] || event;

export function createAlertsView(root, {onSelect = () => {}} = {}) {
  const container = root.getElementById('alerts');
  return {
    render(alerts) {
      container.replaceChildren();
      if (!alerts.length) {
        container.textContent = 'Chưa có cảnh báo hoặc sự kiện.';
        return;
      }
      for (const alert of alerts) {
        const box = root.createElement('button');
        box.type = 'button';
        box.className = 'event event-button';
        const title = root.createElement('b');
        title.textContent = eventTitle(alert.event);
        const details = root.createElement('small');
        details.textContent = formatTime(alert.ts) + (coordinates(alert) ? ' · Xem vị trí trên bản đồ' : ' · Không có GPS fix');
        box.addEventListener('click', () => onSelect(alert));
        box.append(title, details);
        container.append(box);
      }
    },
  };
}
