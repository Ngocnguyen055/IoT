// Both sources provide their own raster tiles. Keep normal browser caching;
// changing source replaces only the background, never GPS markers or tracks.
export const BASEMAPS = {
  osmde: {
    name: 'OpenStreetMap dự phòng',
    url: 'https://tile.openstreetmap.de/{z}/{x}/{y}.png',
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, tiles <a href="https://tile.openstreetmap.de/">FOSSGIS</a>',
  },
  osm: {
    name: 'OpenStreetMap chính',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
};

export function createBasemap(root, leaflet, map) {
  const selector = root.getElementById('basemapSource');
  const status = root.getElementById('mapStatus');
  const retry = root.getElementById('reloadMap');
  let layer, source, loading = true;
  const failed = new Set();

  function renderStatus() {
    if (!status) return;
    status.className = 'map-status muted' + (failed.size ? ' error' : '');
    status.textContent = failed.size
      ? 'Một số ảnh nền bản đồ chưa tải được. Bấm “Tải lại bản đồ” hoặc đổi nguồn nền.'
      : loading ? `Đang tải nền bản đồ · ${source.name}…` : `Nền bản đồ đã tải · ${source.name}`;
  }

  function selectSource() {
    source = BASEMAPS[selector?.value] || BASEMAPS.osmde;
    if (layer) {
      layer.off();
      layer.remove();
    }
    failed.clear();
    loading = true;
    renderStatus();
    map.setMaxZoom(source.maxZoom);
    layer = leaflet.tileLayer(source.url, {
      maxZoom: source.maxZoom, maxNativeZoom: source.maxZoom,
      updateWhenZooming: false, updateWhenIdle: true,
      attribution: source.attribution,
    });
    layer.on('loading', () => { loading = true; renderStatus(); });
    layer.on('tileerror', event => { failed.add(event.tile); renderStatus(); });
    layer.on('tileload', event => { failed.delete(event.tile); renderStatus(); });
    layer.on('tileunload', event => { failed.delete(event.tile); renderStatus(); });
    layer.on('load', () => { loading = false; renderStatus(); });
    layer.addTo(map);
  }

  selector?.addEventListener('change', selectSource);
  retry?.addEventListener('click', () => {
    failed.clear();
    loading = true;
    renderStatus();
    map.invalidateSize({pan: false, debounceMoveend: true});
    layer.redraw();
  });
  selectSource();
}
