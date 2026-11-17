import {coordinates, formatTime} from './format.js';
import {TRACK_GAP_SECONDS} from './config.js';
import {createBasemap} from './basemap.js';

export function trackSegments(points) {
  const segments = [];
  let segment = [], previous = null;
  const flush = () => {
    if (segment.length > 1) segments.push(segment);
    segment = [];
  };
  for (const point of points) {
    const position = coordinates(point);
    if (!position) continue;
    if (previous && point.ts - previous.ts > TRACK_GAP_SECONDS) flush();
    segment.push(position);
    previous = point;
  }
  flush();
  return segments;
}

export function createMapView(root, leaflet = globalThis.L, {ResizeObserverImpl = globalThis.ResizeObserver} = {}) {
  if (!leaflet) {
    root.getElementById('map').textContent = 'Bản đồ chưa tải được. Bạn vẫn có thể xem tọa độ bên dưới.';
    const status = root.getElementById('mapStatus');
    if (status) {
      status.textContent = 'Không tải được thư viện bản đồ. Kiểm tra kết nối Internet rồi tải lại trang.';
      status.className = 'map-status muted error';
    }
    for (const id of ['basemapSource', 'reloadMap']) {
      const control = root.getElementById(id);
      if (control) control.disabled = true;
    }
    return {setPosition() {}, renderTrack() {}, follow: () => false};
  }
  const map = leaflet.map('map').setView([16.4, 106.2], 5);
  createBasemap(root, leaflet, map);
  if (ResizeObserverImpl) {
    const observer = new ResizeObserverImpl(() => map.invalidateSize({pan: false, debounceMoveend: true}));
    observer.observe(root.getElementById('map'));
    map.on('unload', () => observer.disconnect());
  }
  const trackLayers = leaflet.layerGroup().addTo(map);
  let pin = null, firstPositionShown = false;

  return {
    setPosition(point) {
      const position = coordinates(point);
      if (!position) return;
      if (pin) pin.setLatLng(position);
      else pin = leaflet.marker(position).addTo(map);
      pin.bindPopup(`<b>Vị trí GPS gần nhất</b><br>${position[0].toFixed(6)}, ${position[1].toFixed(6)}<br>${formatTime(point.ts)}`);
      if (!firstPositionShown) {
        map.setView(position, 16);
        firstPositionShown = true;
      }
    },
    renderTrack(points, shown) {
      trackLayers.clearLayers();
      if (!shown) return;
      for (const segment of trackSegments(points)) {
        leaflet.polyline(segment, {color: '#38bdf8', weight: 4, opacity: .85}).addTo(trackLayers);
      }
      const first = points.find(point => coordinates(point));
      if (first) {
        leaflet.circleMarker(coordinates(first), {radius: 6, color: '#16a34a', fillOpacity: .9})
          .addTo(trackLayers).bindPopup('Điểm bắt đầu trong khoảng thời gian được chọn');
      }
    },
    follow() {
      if (!pin) return false;
      map.setView(pin.getLatLng(), 17);
      return true;
    },
  };
}
