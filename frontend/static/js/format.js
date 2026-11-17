export const displayValue = value => value === null || value === undefined ? '—' : value;
export const formatTime = seconds => new Date(seconds * 1000).toLocaleString('vi-VN');

export function coordinates(point) {
  if (!point || point.lat === null || point.lat === undefined || point.lon === null || point.lon === undefined) return null;
  const latitude = Number(point.lat), longitude = Number(point.lon);
  return Number.isFinite(latitude) && Number.isFinite(longitude) ? [latitude, longitude] : null;
}
