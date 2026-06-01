import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

// Stub window.location
delete window.location
window.location = { href: 'http://localhost/admin', assign: vi.fn() }

import { useAuth, checkAuth } from '../src/hooks/useAuth.js'

describe('useAuth hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.location.href = 'http://localhost/admin'
  })

  it('returns user on 200 response', async () => {
    const mockUser = { user_id: '1', username: 'alice', role: 'admin', apps: [] }
    authApi.verifyToken.mockResolvedValueOnce(mockUser)

    const { result } = renderHook(() => useAuth())
    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.user).toEqual(mockUser)
    expect(result.current.error).toBeNull()
  })

  it('sets error and null user on 401 response', async () => {
    authApi.verifyToken.mockRejectedValueOnce({ status: 401, error: 'unauthorized' })

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.user).toBeNull()
    expect(result.current.error).toBeTruthy()
  })
})

describe('checkAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.location.href = 'http://localhost/admin'
  })

  it('returns user data on success', async () => {
    const mockUser = { user_id: '1', username: 'alice', role: 'user', apps: ['budget-site'] }
    authApi.verifyToken.mockResolvedValueOnce(mockUser)

    const result = await checkAuth()
    expect(result).toEqual(mockUser)
  })

  it('redirects to /login?redirect=<current href> on failure', async () => {
    authApi.verifyToken.mockRejectedValueOnce({ status: 401 })
    window.location.href = 'http://localhost/admin'

    await checkAuth()

    expect(window.location.href).toContain('/login?redirect=')
  })
})
