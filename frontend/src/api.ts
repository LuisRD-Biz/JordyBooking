export async function api<T = any>(path: string, method = 'GET', body?: unknown, headers: Record<string,string> = {}): Promise<T> {
  const response = await fetch(path, {method, credentials: 'same-origin', headers: {'Content-Type': 'application/json', ...headers}, body: body === undefined ? undefined : JSON.stringify(body)});
  if (!response.ok) {
    if (response.status === 401 && path.startsWith('/api/')) window.dispatchEvent(new Event('session-expired'));
    const error = await response.json().catch(() => ({detail: 'No se pudo conectar con el estudio.'}));
    throw new Error(Array.isArray(error.detail) ? error.detail.map((d: any) => `${d.loc.slice(1).join(' ')}: ${d.msg}`).join('. ') : error.detail || 'No se pudo completar la operación.');
  }
  return response.json();
}
export async function all(path: string) {
  const result = [];
  for (let offset = 0; ; offset += 200) {
    const batch = await api<any[]>(`${path}?limit=200&offset=${offset}`);
    result.push(...batch);
    if (batch.length < 200) return result;
  }
}
