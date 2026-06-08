const DEFAULT_HEADERS = {
  'Content-Type': 'application/json'
}

export async function httpJson(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(path, {
    method,
    headers: DEFAULT_HEADERS,
    body: body ? JSON.stringify(body) : undefined,
    signal
  })

  if (!res.ok) {
    let detail = ''
    try {
      const data = await res.json()
      detail = data?.detail ? String(data.detail) : JSON.stringify(data)
    } catch {
      try {
        detail = await res.text()
      } catch {
        detail = ''
      }
    }
    throw new Error(detail || `Request failed: ${res.status}`)
  }

  return res.json()
}
