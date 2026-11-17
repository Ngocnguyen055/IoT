import {coordinates, formatTime} from './format.js';
import {LOCATION_FRESH_SECONDS} from './config.js';

export function createLocationView(root, map, {clipboard = globalThis.navigator?.clipboard, timers = globalThis} = {}) {
  const element = id => root.getElementById(id);
  let savedCoordinates = null, seenLocation = null;

  element('copyCoords').addEventListener('click', async () => {
    if (!savedCoordinates) return;
    try {
      await clipboard.writeText(savedCoordinates);
      element('copyCoords').textContent = 'Đã sao chép';
    } catch {
      element('copyCoords').textContent = 'Không thể sao chép';
    }
    timers.setTimeout(() => { element('copyCoords').textContent = 'Sao chép tọa độ'; }, 1600);
  });

  return {
    render(point, now, device) {
      const position = coordinates(point);
      const state = element('locationState');
      if (!position) {
        state.textContent = 'Chưa có GPS Fix';
        state.className = 'location-tag none';
        element('position').textContent = 'Chưa ghi nhận được tọa độ GPS hợp lệ.';
        element('locationTime').textContent = 'Thời gian cập nhật: —';
        element('googleMaps').hidden = true;
        element('copyCoords').disabled = true;
        savedCoordinates = null;
        return;
      }
      const age = Math.max(0, now - point.ts);
      const fresh = age <= LOCATION_FRESH_SECONDS;
      state.textContent = fresh ? 'Đã có vị trí' : 'Vị trí cũ';
      state.className = 'location-tag ' + (fresh ? 'current' : 'stale');
      savedCoordinates = `${position[0].toFixed(6)}, ${position[1].toFixed(6)}`;
      element('position').textContent = `Tọa độ: ${savedCoordinates}`;
      element('locationTime').textContent = `Cập nhật lần cuối: ${formatTime(point.ts)} · ${Math.floor(age / 60)} phút trước${device ? ' · Thiết bị: ' + device : ''}`;
      element('copyCoords').disabled = false;
      element('googleMaps').href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(savedCoordinates)}`;
      element('googleMaps').hidden = false;
      const key = `${position[0]},${position[1]},${point.ts}`;
      if (key !== seenLocation) {
        seenLocation = key;
        map.setPosition({...point, lat: position[0], lon: position[1]});
      }
    },
  };
}
