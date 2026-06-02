import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AppAccessCheckboxes from '../src/components/AppAccessCheckboxes.jsx'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

const ALL_APPS = [
  'budget-site',
  'family-admin-routine',
  'family-archive',
  'family-kitchen-recipes',
  'new-site',
  'portuguese-expenses',
  'reminders-app',
  'servinga-dashboard',
]

const mockApps = ALL_APPS.map((name, i) => ({
  app_name: name,
  is_enabled: i === 0,
}))

describe('AppAccessCheckboxes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authApi.getApps.mockResolvedValue(mockApps)
    authApi.putApps.mockResolvedValue(mockApps)
  })

  it('renders 8 checkboxes after loading', async () => {
    render(<AppAccessCheckboxes userId="u1" />)
    await waitFor(() =>
      expect(screen.getAllByRole('checkbox').length).toBe(8)
    )
  })

  it('first checkbox is checked, rest unchecked', async () => {
    render(<AppAccessCheckboxes userId="u1" />)
    await waitFor(() => expect(screen.getAllByRole('checkbox').length).toBe(8))

    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes[0]).toBeChecked()
    checkboxes.slice(1).forEach((cb) => expect(cb).not.toBeChecked())
  })

  it('onChange propagates putApps call when Save is clicked', async () => {
    render(<AppAccessCheckboxes userId="u1" />)
    await waitFor(() => expect(screen.getAllByRole('checkbox').length).toBe(8))

    const user = userEvent.setup()
    // toggle second checkbox on
    await user.click(screen.getAllByRole('checkbox')[1])
    await user.click(screen.getByRole('button', { name: /admin\.apps_save/i }))

    expect(authApi.putApps).toHaveBeenCalledWith(
      'u1',
      expect.arrayContaining([
        expect.objectContaining({ app_name: 'budget-site', is_enabled: true }),
        expect.objectContaining({ app_name: 'family-admin-routine', is_enabled: true }),
      ])
    )
  })
})
