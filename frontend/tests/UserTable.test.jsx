import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UserTable from '../src/components/UserTable.jsx'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

const mockUsers = [
  { id: 'u1', username: 'alice', email: 'alice@example.com', role: 'user', is_active: true },
  { id: 'u2', username: 'bob', email: null, role: 'user', is_active: false },
]

describe('UserTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authApi.getApps.mockResolvedValue([
      { app_name: 'budget-site', is_enabled: true },
      { app_name: 'family-admin-routine', is_enabled: false },
      { app_name: 'family-archive', is_enabled: false },
      { app_name: 'family-kitchen-recipes', is_enabled: false },
      { app_name: 'new-site', is_enabled: false },
      { app_name: 'portuguese-expenses', is_enabled: false },
      { app_name: 'reminders-app', is_enabled: false },
      { app_name: 'servinga-dashboard', is_enabled: false },
    ])
    authApi.putApps.mockResolvedValue([])
  })

  it('renders rows with username, email, role, and status', () => {
    render(<UserTable users={mockUsers} onUsersChange={vi.fn()} />)
    expect(screen.getByText('alice')).toBeInTheDocument()
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.getAllByText('user').length).toBeGreaterThanOrEqual(1)
    // active chip
    expect(screen.getByText('admin.status_active')).toBeInTheDocument()
    // blocked chip
    expect(screen.getByText('admin.status_blocked')).toBeInTheDocument()
  })

  it('Block button triggers patchUser with correct user id', async () => {
    authApi.patchUser.mockResolvedValueOnce({ id: 'u1', username: 'alice', is_active: false })
    const onUsersChange = vi.fn()
    render(<UserTable users={mockUsers} onUsersChange={onUsersChange} />)
    const user = userEvent.setup()

    const blockBtn = screen.getByLabelText('admin.btn_block alice')
    await user.click(blockBtn)

    expect(authApi.patchUser).toHaveBeenCalledWith('u1', { is_active: false })
    await waitFor(() => expect(onUsersChange).toHaveBeenCalled())
  })

  it('shows error message when block/unblock fails', async () => {
    authApi.patchUser.mockRejectedValueOnce({ status: 500 })
    render(<UserTable users={mockUsers} onUsersChange={vi.fn()} />)
    const user = userEvent.setup()

    await user.click(screen.getByLabelText('admin.btn_block alice'))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('admin.error_unknown')
    )
  })

  it('clicking App Access expands and renders AppAccessCheckboxes', async () => {
    render(<UserTable users={[mockUsers[0]]} onUsersChange={vi.fn()} />)
    const user = userEvent.setup()

    const appBtn = screen.getByLabelText('admin.btn_app_access alice')
    await user.click(appBtn)

    await waitFor(() =>
      expect(screen.getByText('admin.apps_title')).toBeInTheDocument()
    )
  })
})
