import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AdminPage from '../src/pages/AdminPage.jsx'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

vi.mock('../src/components/UserTable.jsx', () => ({
  default: ({ users }) => (
    <table>
      <tbody>
        {users.map((u) => (
          <tr key={u.id}>
            <td>{u.username}</td>
          </tr>
        ))}
      </tbody>
    </table>
  ),
}))
vi.mock('../src/components/UserCreateModal.jsx', () => ({
  default: ({ isOpen, onCreated }) =>
    isOpen ? (
      <button onClick={() => onCreated({ id: 'new', username: 'newuser', role: 'user', is_active: true })}>
        modal-create
      </button>
    ) : null,
}))
vi.mock('../src/components/LanguageSwitcher.jsx', () => ({
  default: () => <div data-testid="lang-switcher" />,
}))

const mockUser = { user_id: 'a1', username: 'admin', role: 'admin', apps: [] }
const mockUsers = [
  { id: 'u1', username: 'alice', email: null, role: 'user', is_active: true },
]

function renderPage(user = mockUser) {
  const setUser = vi.fn()
  render(
    <MemoryRouter>
      <AdminPage user={user} setUser={setUser} />
    </MemoryRouter>
  )
  return { setUser }
}

describe('AdminPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading spinner initially', () => {
    authApi.getUsers.mockReturnValue(new Promise(() => {}))
    renderPage()
    // Spinner should be present
    expect(screen.queryByText('admin.title')).toBeInTheDocument()
  })

  it('renders user list after load', async () => {
    authApi.getUsers.mockResolvedValueOnce(mockUsers)
    renderPage()
    await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument())
  })

  it('shows error on 403 response', async () => {
    authApi.getUsers.mockRejectedValueOnce({ status: 403 })
    renderPage()
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('admin.error_forbidden')
    )
  })

  it('opens modal when Create User button is clicked', async () => {
    authApi.getUsers.mockResolvedValueOnce(mockUsers)
    renderPage()
    await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument())

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /admin\.create_user/i }))
    expect(screen.getByText('modal-create')).toBeInTheDocument()
  })

  it('calls logout and clears user on sign out', async () => {
    authApi.getUsers.mockResolvedValueOnce(mockUsers)
    authApi.logout.mockResolvedValueOnce(true)
    const { setUser } = renderPage()
    await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument())

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /app\.logout/i }))

    expect(authApi.logout).toHaveBeenCalled()
    await waitFor(() => expect(setUser).toHaveBeenCalledWith(null))
  })
})
