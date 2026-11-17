export class LoginRequiredError extends Error {
  constructor() {
    super('Cần đăng nhập');
    this.name = 'LoginRequiredError';
  }
}

export function createApi({fetchImpl = globalThis.fetch.bind(globalThis), onUnauthorized = () => globalThis.location.assign('/login')} = {}) {
  let redirected = false;

  async function request(url, message, options = {}) {
    const response = await fetchImpl(url, {cache: 'no-store', credentials: 'same-origin', ...options});
    if (response.status === 401) {
      if (!redirected) {
        redirected = true;
        onUnauthorized();
      }
      throw new LoginRequiredError();
    }
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.error || message);
    }
    return response.json();
  }

  return {
    status: () => request('/api/status', 'Không thể đọc API'),
    track: (device, hours) => request(`/api/track?device_id=${encodeURIComponent(device)}&hours=${hours}`, 'Không thể đọc lịch sử GPS'),
    locate: device => request('/api/command', 'Không thể gửi lệnh định vị', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({device_id: device, command: 'LOCATE'}),
    }),
  };
}
