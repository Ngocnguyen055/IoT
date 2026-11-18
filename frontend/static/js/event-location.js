import {LoginRequiredError} from './api.js';
import {eventTitle} from './alerts.js';
import {coordinates, formatTime} from './format.js';

export function createEventLocation({root, api, map, search = ''}) {
  const element = id => root.getElementById(id);
  const panel = element('eventLocation');
  if (!panel) return {select() {}, async openLinked() {}};
  const title = element('eventLocationTitle');
  const time = element('eventLocationTime');
  const message = element('eventLocationMessage');
  const googleMaps = element('eventGoogleMaps');
  let requestVersion = 0;

  function reveal() {
    panel.hidden = false;
    panel.scrollIntoView?.({behavior: 'smooth', block: 'start'});
  }

  function render(item) {
    title.textContent = eventTitle(item.event);
    time.textContent = `${formatTime(item.ts)} · Thiết bị: ${item.device_id}`;
    const position = coordinates(item);
    googleMaps.hidden = !position;
    if (!position) {
      map.clearEvent();
      message.textContent = 'Không có tọa độ GPS được lưu cùng sự kiện này. Chưa xác định được vị trí tại thời điểm cảnh báo.';
    } else {
      const text = position.map(value => value.toFixed(6)).join(', ');
      const popup = root.createElement('div');
      const heading = root.createElement('b'), details = root.createElement('p');
      heading.textContent = eventTitle(item.event);
      details.textContent = `${formatTime(item.ts)} · ${item.device_id} · ${text}`;
      popup.append(heading, details);
      const shown = map.showEvent(item, popup);
      message.textContent = `Tọa độ tại thời điểm sự kiện: ${text}. ` + (shown
        ? 'Điểm màu cam đánh dấu sự kiện đã chọn; ghim vị trí mới nhất của thiết bị vẫn được cập nhật riêng.'
        : 'Bản đồ chưa tải được. Bạn có thể mở vị trí này trên Google Maps.');
      googleMaps.href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(text)}`;
    }
    reveal();
  }

  function error(text) {
    map.clearEvent();
    title.textContent = 'Vị trí sự kiện';
    time.textContent = '';
    googleMaps.hidden = true;
    message.textContent = text;
    reveal();
  }

  element('closeEventLocation').addEventListener('click', () => {
    requestVersion++;
    map.clearEvent();
    panel.hidden = true;
  });

  return {
    select(item) {
      requestVersion++;
      render(item);
    },
    async openLinked() {
      const identifier = new URLSearchParams(search).get('event');
      if (identifier === null) return;
      const version = ++requestVersion;
      if (!/^[1-9][0-9]{0,18}$/.test(identifier)) {
        error('Liên kết sự kiện không hợp lệ.');
        return;
      }
      title.textContent = 'Vị trí sự kiện';
      time.textContent = '';
      googleMaps.hidden = true;
      message.textContent = 'Đang đọc sự kiện…';
      reveal();
      try {
        const response = await api.alert(identifier);
        if (version === requestVersion) render(response.item);
      } catch (failure) {
        if (version === requestVersion && !(failure instanceof LoginRequiredError)) {
          error(failure.message || 'Không thể đọc sự kiện. Bạn thử tải lại trang nhé.');
        }
      }
    },
  };
}
