import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UserCreateModal from '../src/components/UserCreateModal.jsx'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

function renderModal(props = {}) {
  const onClose = props.onClose || vi.fn()
  const onCreated = props.onCreated || vi.fn()
  render(
    <UserCreateModal
      isOpen={props.isOpen !== false}
      onClose={onClose}
      onCreated={onCreated}
    />
  )
  return { onClose, onCreated }
}

describe('UserCreateModal', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders form fields when open', () => {
    renderModal()
    expect(screen.getByLabelText('admin.modal_username')).toBeInTheDocument()
    expect(screen.getByLabelText('admin.modal_email')).toBeInTheDocument()
    expect(screen.getByLabelText('admin.modal_password')).toBeInTheDocument()
  })

  it('shows validation error when username is empty on submit', async () => {
    renderModal()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /admin\.modal_submit/i }))
    expect(screen.getByRole('alert')).toHaveTextContent('admin.error_username_required')
  })

  it('shows validation error when password is empty', async () => {
    renderModal()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('admin.modal_username'), 'bob')
    await user.click(screen.getByRole('button', { name: /admin\.modal_submit/i }))
    expect(screen.getByRole('alert')).toHaveTextContent('admin.error_password_required')
  })

  it('calls createUser and invokes onCreated on success', async () => {
    const newUser = { id: 'u3', username: 'bob', email: null, role: 'user', is_active: true }
    authApi.createUser.mockResolvedValueOnce(newUser)
    const { onCreated } = renderModal()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('admin.modal_username'), 'bob')
    await user.type(screen.getByLabelText('admin.modal_password'), 'pass123')
    await user.click(screen.getByRole('button', { name: /admin\.modal_submit/i }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(newUser))
  })

  it('shows conflict error on 409 response', async () => {
    authApi.createUser.mockRejectedValueOnce({ status: 409 })
    renderModal()
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('admin.modal_username'), 'alice')
    await user.type(screen.getByLabelText('admin.modal_password'), 'pass')
    await user.click(screen.getByRole('button', { name: /admin\.modal_submit/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('admin.error_conflict')
    )
  })

  it('Cancel button calls onClose', async () => {
    const { onClose } = renderModal()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /admin\.modal_cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
