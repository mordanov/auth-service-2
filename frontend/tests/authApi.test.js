import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  login,
  logout,
  verifyToken,
  getUsers,
  createUser,
  patchUser,
  getApps,
  putApps,
} from '../src/api/authApi.js'

function mockFetch(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

describe('authApi', () => {
  beforeEach(() => {
    global.fetch = mockFetch(200, { message: 'ok' })
  })
  afterEach(() => vi.restoreAllMocks())

  describe('login', () => {
    it('returns data on 200', async () => {
      global.fetch = mockFetch(200, { message: 'ok' })
      const result = await login('alice', 'pass')
      expect(result).toEqual({ message: 'ok' })
    })

    it('throws on 401', async () => {
      global.fetch = mockFetch(401, { error: 'invalid_credentials' })
      await expect(login('a', 'b')).rejects.toMatchObject({ status: 401 })
    })

    it('throws on 403', async () => {
      global.fetch = mockFetch(403, { error: 'forbidden' })
      await expect(login('a', 'b')).rejects.toMatchObject({ status: 403 })
    })
  })

  describe('logout', () => {
    it('returns true on 200', async () => {
      const result = await logout()
      expect(result).toBe(true)
    })

    it('returns false on 500', async () => {
      global.fetch = mockFetch(500, {})
      const result = await logout()
      expect(result).toBe(false)
    })
  })

  describe('verifyToken', () => {
    it('returns user data on 200', async () => {
      global.fetch = mockFetch(200, { user_id: '1', username: 'alice', role: 'admin', apps: [] })
      const result = await verifyToken()
      expect(result.username).toBe('alice')
    })

    it('throws on 401', async () => {
      global.fetch = mockFetch(401, { error: 'unauthorized' })
      await expect(verifyToken()).rejects.toMatchObject({ status: 401 })
    })

    it('throws on 403', async () => {
      global.fetch = mockFetch(403, { error: 'forbidden' })
      await expect(verifyToken()).rejects.toMatchObject({ status: 403 })
    })
  })

  describe('admin endpoints', () => {
    it('getUsers returns array on 200', async () => {
      global.fetch = mockFetch(200, [{ id: 'u1' }])
      const result = await getUsers()
      expect(result).toHaveLength(1)
    })

    it('getUsers throws on 403', async () => {
      global.fetch = mockFetch(403, {})
      await expect(getUsers()).rejects.toMatchObject({ status: 403 })
    })

    it('createUser returns new user on 201', async () => {
      global.fetch = mockFetch(201, { id: 'u2', username: 'bob' })
      const result = await createUser({ username: 'bob', password: 'pass', role: 'user' })
      expect(result.username).toBe('bob')
    })

    it('createUser throws on 409', async () => {
      global.fetch = mockFetch(409, { error: 'conflict' })
      await expect(createUser({ username: 'bob', password: 'pass' })).rejects.toMatchObject({ status: 409 })
    })

    it('patchUser returns updated user on 200', async () => {
      global.fetch = mockFetch(200, { id: 'u1', is_active: false })
      const result = await patchUser('u1', { is_active: false })
      expect(result.is_active).toBe(false)
    })

    it('getApps returns app list on 200', async () => {
      global.fetch = mockFetch(200, [{ app_name: 'budget-site', is_enabled: true }])
      const result = await getApps('u1')
      expect(result[0].app_name).toBe('budget-site')
    })

    it('putApps returns updated list on 200', async () => {
      global.fetch = mockFetch(200, [{ app_name: 'budget-site', is_enabled: false }])
      const result = await putApps('u1', [{ app_name: 'budget-site', is_enabled: false }])
      expect(result[0].is_enabled).toBe(false)
    })
  })
})
