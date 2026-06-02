import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from '../src/components/LoginForm.jsx'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

function renderForm(props = {}) {
  const onSuccess = props.onSuccess || vi.fn()
  render(<LoginForm onSuccess={onSuccess} redirectUrl={props.redirectUrl} />)
  return { onSuccess }
}

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders username and password fields', () => {
    renderForm()
    expect(screen.getByLabelText('login.username')).toBeInTheDocument()
    expect(screen.getByLabelText('login.password')).toBeInTheDocument()
  })

  it('submit button is disabled when fields are empty', () => {
    renderForm()
    const btn = screen.getByRole('button', { name: /login\.submit/i })
    expect(btn).toBeDisabled()
  })

  it('calls login() with username and password on submit', async () => {
    authApi.login.mockResolvedValueOnce({ message: 'ok' })
    const { onSuccess } = renderForm({ redirectUrl: '/dashboard' })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('login.username'), 'alice')
    await user.type(screen.getByLabelText('login.password'), 'secret')
    await user.click(screen.getByRole('button', { name: /login\.submit/i }))

    expect(authApi.login).toHaveBeenCalledWith('alice', 'secret')
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith('/dashboard'))
  })

  it('shows error message on 401 response', async () => {
    authApi.login.mockRejectedValueOnce({ status: 401, error: 'invalid_credentials' })
    renderForm()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('login.username'), 'alice')
    await user.type(screen.getByLabelText('login.password'), 'wrong')
    await user.click(screen.getByRole('button', { name: /login\.submit/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('login.error_invalid_credentials')
    )
  })

  it('shows forbidden error on 403 response', async () => {
    authApi.login.mockRejectedValueOnce({ status: 403, error: 'forbidden' })
    renderForm()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('login.username'), 'blocked')
    await user.type(screen.getByLabelText('login.password'), 'pass')
    await user.click(screen.getByRole('button', { name: /login\.submit/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('login.error_forbidden')
    )
  })

  it('shows generic error on unknown failure', async () => {
    authApi.login.mockRejectedValueOnce({ status: 500 })
    renderForm()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('login.username'), 'alice')
    await user.type(screen.getByLabelText('login.password'), 'pass')
    await user.click(screen.getByRole('button', { name: /login\.submit/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('login.error_unknown')
    )
  })
})
