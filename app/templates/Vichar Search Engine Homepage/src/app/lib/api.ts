const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/$/, '');

export const API_BASE_URL =
  configuredApiBase || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

export function buildApiUrl(path: string, params?: Record<string, string | number>) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, String(value));
    });
  }

  if (!API_BASE_URL) {
    return `${url.pathname}${url.search}`;
  }

  return url.toString();
}
