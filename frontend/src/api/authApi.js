const BASE = ''

async function request(method, path, body) {
  const opts = {
    method,
    credentials: 'include',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
  }
  if (body !== undefined) {
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`${BASE}${path}`, opts)
  return res
}

// ── Auth ────────────────────────────────────────────────────────────────────

export async function login(username, password) {
  const res = await request('POST', '/api/auth/login', { username, password })
  const data = await res.json()
  if (!res.ok) {
    throw { status: res.status, error: data.error || 'unknown' }
  }
  return data
}

export async function logout() {
  const res = await request('POST', '/api/auth/logout')
  return res.ok
}

export async function verifyToken() {
  const res = await request('GET', '/api/verify-token')
  if (res.status === 401 || res.status === 403) {
    throw { status: res.status, error: 'unauthorized' }
  }
  if (!res.ok) {
    throw { status: res.status, error: 'unknown' }
  }
  return res.json()
}

// ── Admin ───────────────────────────────────────────────────────────────────

export async function getUsers() {
  const res = await request('GET', '/api/admin/users')
  if (!res.ok) throw { status: res.status }
  return res.json()
}

export async function createUser(data) {
  const res = await request('POST', '/api/admin/users', data)
  const json = await res.json()
  if (!res.ok) throw { status: res.status, error: json.error, detail: json.detail }
  return json
}

export async function patchUser(id, data) {
  const res = await request('PATCH', `/api/admin/users/${id}`, data)
  if (!res.ok) throw { status: res.status }
  return res.json()
}

export async function getApps(userId) {
  const res = await request('GET', `/api/admin/users/${userId}/apps`)
  if (!res.ok) throw { status: res.status }
  return res.json()
}

export async function putApps(userId, apps) {
  const res = await request('PUT', `/api/admin/users/${userId}/apps`, apps)
  if (!res.ok) throw { status: res.status }
  return res.json()
}
