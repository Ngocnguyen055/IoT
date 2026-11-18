import {createApi, LoginRequiredError} from './api.js';
import {eventTitle} from './alerts.js';
import {coordinates, formatTime} from './format.js';

const measurement = (value, unit) => value === null || value === undefined ? '—' : `${value} ${unit}`;

export function createHistoryView(root) {
  const element = id => root.getElementById(id);
  const notice = element('historyNotice');
  const rows = element('historyRows');
  const cell = text => {
    const result = root.createElement('td');
    result.textContent = text;
    return result;
  };
  return {
    onPrevious: handler => element('historyPrevious').addEventListener('click', handler),
    onNext: handler => element('historyNext').addEventListener('click', handler),
    onRefresh: handler => element('historyRefresh').addEventListener('click', handler),
    busy(value, pagination) {
      element('historyPrevious').disabled = value || !pagination?.has_previous;
      element('historyNext').disabled = value || !pagination?.has_next;
      element('historyRefresh').disabled = value;
      rows.ariaBusy = String(value);
    },
    loading() {
      notice.className = 'notice';
      notice.textContent = 'Đang tải lịch sử…';
    },
    render(items, page) {
      rows.replaceChildren();
      if (!items.length) {
        const row = root.createElement('tr'), message = cell('Chưa có cảnh báo hoặc sự kiện.');
        message.colSpan = 7;
        message.className = 'history-empty';
        row.append(message);
        rows.append(row);
      }
      for (const item of items) {
        const row = root.createElement('tr');
        const event = root.createElement('td'), badge = root.createElement('a');
        badge.className = 'event-badge event-location-link' + (item.event === 'button' ? ' danger' : ['high_bpm', 'low_spo2'].includes(item.event) ? ' warning' : '');
        badge.href = `/?event=${encodeURIComponent(item.id)}#eventLocation`;
        badge.title = 'Xem vị trí đã lưu của sự kiện';
        badge.textContent = eventTitle(item.event);
        event.append(badge);
        const position = coordinates(item);
        const location = cell('Chưa có tọa độ');
        if (position) {
          const link = root.createElement('a');
          link.className = 'text-link';
          link.href = badge.href;
          link.textContent = position.map(value => value.toFixed(5)).join(', ');
          location.replaceChildren(link);
        }
        row.append(cell(formatTime(item.ts)), event, cell(item.device_id), cell(measurement(item.bpm, 'BPM')),
          cell(measurement(item.spo2, '%')), cell(measurement(item.battery_pct, '%')),
          location);
        rows.append(row);
      }
      element('historyPage').textContent = `Trang ${page}`;
      element('historyCount').textContent = `${items.length} sự kiện`;
      element('historyTable').scrollTop = 0;
      notice.className = 'notice';
      notice.textContent = items.length ? 'Chọn “Về mới nhất” để cập nhật các sự kiện vừa đến.' : 'Chưa có lịch sử cảnh báo.';
    },
    error(error) {
      notice.className = 'notice error';
      notice.textContent = error.message || 'Không thể tải lịch sử. Vui lòng thử lại.';
    },
  };
}

export function createHistoryController({api, view}) {
  let pagination = null, page = 1, pending = null;

  function load(parameters = {}, targetPage = 1) {
    if (pending) return pending;
    view.busy(true, pagination);
    view.loading();
    pending = (async () => {
      try {
        const response = await api.alerts(parameters);
        pagination = response.pagination;
        page = targetPage;
        view.render(response.items, page);
      } catch (error) {
        if (!(error instanceof LoginRequiredError)) view.error(error);
      } finally {
        view.busy(false, pagination);
      }
    })().finally(() => { pending = null; });
    return pending;
  }

  view.onNext(() => pagination?.has_next ? load({snapshot: pagination.snapshot, before: pagination.next_before}, page + 1) : undefined);
  view.onPrevious(() => pagination?.has_previous ? load({snapshot: pagination.snapshot, after: pagination.previous_after}, Math.max(1, page - 1)) : undefined);
  view.onRefresh(() => load({}, 1));
  return {refresh: () => load({}, 1)};
}

export function mountHistory({root = globalThis.document, api = createApi()} = {}) {
  return createHistoryController({api, view: createHistoryView(root)});
}

if (typeof document !== 'undefined' && document.getElementById('historyRows')) {
  void mountHistory().refresh();
}
