const el = id => document.getElementById(id);
const map = L.map('map').setView([16.4,106.2], 5); // Default map view, NOT a device position
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19, attribution: '© OpenStreetMap contributors'
}).addTo(map);
let pin = null;
let seenLocation = null;
let savedCoords = null;
let trackLayers = L.layerGroup().addTo(map);
let trackSignature = '';
let firstPositionShown = false;
let trackingBusy = false;
let lastDevice = 'ngoc-01';
const fmt = v => v === null || v === undefined ? '—' : v;
const when = sec => new Date(sec * 1000).toLocaleString('vi-VN');
function setLastLocation(p, now, device) {
  const state = el('locationState');
  if (!p || !Number.isFinite(Number(p.lat)) || !Number.isFinite(Number(p.lon))) {
    state.textContent = 'Chưa có GPS Fix';
    state.className = 'location-tag none';
    el('position').textContent = 'Chưa ghi nhận được tọa độ GPS hợp lệ.';
    el('locationTime').textContent = 'Thời gian cập nhật: —';
    el('googleMaps').hidden = true;
    el('copyCoords').disabled = true;
    savedCoords = null;
    return;
  }
  const lat = Number(p.lat), lon = Number(p.lon);
  const age = Math.max(0, now - p.ts);
  const fresh = age <= 300;
  state.textContent = fresh ? 'Đã có vị trí' : 'Vị trí cũ';
  state.className = 'location-tag ' + (fresh ? 'current' : 'stale');
  el('position').textContent = `Tọa độ: ${lat.toFixed(6)}, ${lon.toFixed(6)}`;
  el('locationTime').textContent = `Cập nhật lần cuối: ${when(p.ts)} · ${Math.floor(age/60)} phút trước${device ? ' · Thiết bị: '+device : ''}`;
  savedCoords = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
  el('copyCoords').disabled = false;
  const link = el('googleMaps');
  link.href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(savedCoords)}`;
  link.hidden = false;
  const key = `${lat},${lon},${p.ts}`;
  if (key !== seenLocation) {
    seenLocation = key;
    if (pin) pin.setLatLng([lat,lon]); else pin = L.marker([lat,lon]).addTo(map);
    pin.bindPopup(`<b>Vị trí GPS gần nhất</b><br>${lat.toFixed(6)}, ${lon.toFixed(6)}<br>${when(p.ts)}`);
    if (!firstPositionShown) { map.setView([lat,lon], 16); firstPositionShown = true; }
  }
}
async function refresh() {
  try {
    const r = await fetch('/api/status', {cache:'no-store'});
    if (r.status===401) { location.assign('/login'); return; }
    if (!r.ok) throw Error('Không thể đọc API');
    const d = await r.json(), x = d.latest;
    el('connection').textContent = !x ? 'Chưa có dữ liệu từ ESP32' : d.now-x.ts>90 ? 'Thiết bị có thể đang ngoại tuyến — dữ liệu cuối đã cũ' : 'Đã nhận dữ liệu thiết bị';
    if (x) {
      el('bpm').textContent=fmt(x.bpm); el('spo2').textContent=fmt(x.spo2);
      el('battery').textContent=fmt(x.battery_pct); el('voltage').textContent=fmt(x.battery_voltage);
      el('device').textContent=x.device_id; el('sat').textContent=fmt(x.gps_satellites);
      el('current').textContent=fmt(x.current_ma); el('time').textContent=when(x.ts);
    }
    lastDevice = x?.device_id || d.last_location?.device_id || 'ngoc-01';
    el('command').textContent=(d.commands.find(c=>c.device_id===(x?.device_id||'ngoc-01'))||{}).cmd||'NONE';
    setLastLocation(d.last_location, d.now, d.last_location?.device_id || x?.device_id);
    await refreshTrack();
    el('alerts').replaceChildren();
    for (const a of d.alerts) {
      const box=document.createElement('div'); box.className='event';
      const title=document.createElement('b'); title.textContent=({button:'Nhấn nút SOS',high_bpm:'Cảnh báo BPM trên ngưỡng',low_spo2:'Cảnh báo SpO₂ thấp',remote:'Định vị từ website'}[a.event]||a.event);
      const sub=document.createElement('small'); sub.textContent=when(a.ts)+(a.lat==null?' · Không có GPS fix':' · Có tọa độ');
      box.append(title,sub); el('alerts').append(box);
    }
  } catch(e) { el('connection').textContent='Lỗi tải dữ liệu: '+e.message; }
}

async function refreshTrack(force = false) {
  if (trackingBusy) return;
  trackingBusy = true;
  try {
    const hours = Number(el('trackHours').value);
    const r = await fetch(`/api/track?device_id=${encodeURIComponent(lastDevice)}&hours=${hours}`, {cache:'no-store'});
    if (!r.ok) throw Error('Không thể đọc lịch sử GPS');
    const data = await r.json();
    const points = data.points || [];
    const first = points[0], last = points[points.length-1];
    const signature = `${lastDevice}:${hours}:${points.length}:${first?.id}:${last?.id}`;
    const shown = el('showTrack').checked;
    if (force || signature !== trackSignature) {
      trackSignature = signature;
      trackLayers.clearLayers();
      if (shown) {
        // Discontinue paths across long outages; never invent an intermediate route.
        let segment = [], previous = null;
        const flush = () => { if (segment.length > 1) L.polyline(segment, {color:'#38bdf8',weight:4,opacity:.85}).addTo(trackLayers); segment=[]; };
        for (const p of points) {
          const pos = [Number(p.lat), Number(p.lon)];
          if (!Number.isFinite(pos[0]) || !Number.isFinite(pos[1])) continue;
          if (previous && p.ts - previous.ts > 120) flush();
          segment.push(pos); previous = p;
        }
        flush();
        if (points.length) {
          L.circleMarker([Number(first.lat),Number(first.lon)], {radius:6,color:'#16a34a',fillOpacity:.9}).addTo(trackLayers).bindPopup('Điểm bắt đầu trong khoảng thời gian được chọn');
        }
      }
    }
    const lastTime = last ? when(last.ts) : '—';
    el('trackingStatus').textContent = `${points.length} điểm GPS (${hours} giờ) · Điểm cuối: ${lastTime}` + (points.length >= 1000 ? ' · Đã giới hạn 1000 điểm' : '');
  } catch(e) { el('trackingStatus').textContent='Lỗi tải hành trình: '+e.message; }
  finally { trackingBusy = false; }
}
el('trackHours').addEventListener('change', () => { trackSignature=''; refreshTrack(true); });
el('showTrack').addEventListener('change', () => { trackSignature=''; refreshTrack(true); });
el('followGps').addEventListener('click', () => {
  if (pin) map.setView(pin.getLatLng(), 17);
  else el('trackingStatus').textContent = 'Chưa có vị trí GPS hợp lệ để định tâm bản đồ';
});

el('copyCoords').addEventListener('click', async () => {
  if (!savedCoords) return;
  try { await navigator.clipboard.writeText(savedCoords); el('copyCoords').textContent='Đã sao chép'; }
  catch(e) { el('copyCoords').textContent='Không thể sao chép'; }
  setTimeout(()=>el('copyCoords').textContent='Sao chép tọa độ',1600);
});
el('locate').addEventListener('click',async()=>{
  el('locate').disabled=true;
  try {
    const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:el('device').textContent==='—'?'ngoc-01':el('device').textContent,command:'LOCATE'})});
    const d=await r.json(); el('commandMessage').textContent=d.message||d.error;
  } catch(e) {el('commandMessage').textContent=e.message;}
  finally {el('locate').disabled=false;refresh();}
});
refresh();setInterval(refresh,5000);
