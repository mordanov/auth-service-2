import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../src/pages/LoginPage.jsx'
import * as authApi from '../src/api/authApi.js'

vi.mock('../src/api/authApi.js')

// Stub child components to isolate page logic
vi.mock('../src/components/LoginForm.jsx', () => ({
  default: ({ onSuccess, redirectUrl }) => (
    <button onClick={() => onSuccess(redirectUrl || '/')}>login-form-submit</button>
  ),
}))
vi.mock('../src/components/OAuthButtons.jsx', () => ({
  default: ({ error }) => <div data-testid="oauth-buttons" data-error={String(error)} />,
}))
vi.mock('../src/components/LanguageSwitcher.jsx', () => ({
  default: () => <div data-testid="lang-switcher" />,
}))

function renderPage(search = '') {
  return render(
    <MemoryRouter initialEntries={[`/login${search}`]}>
      <LoginPage />
    </MemoryRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders login title and language switcher', () => {
    renderPage()
    expect(screen.getByText('login.title')).toBeInTheDocument()
    expect(screen.getByTestId('lang-switcher')).toBeInTheDocument()
  })

  it('renders password, Google, and GitHub tabs', () => {
    renderPage()
    expect(screen.getByText('login.tabPassword')).toBeInTheDocument()
    expect(screen.getByText('login.tabGoogle')).toBeInTheDocument()
    expect(screen.getByText('login.tabGithub')).toBeInTheDocument()
  })

  it('passes forbidden error to OAuthButtons when ?error=forbidden and Google tab is active', async () => {
    renderPage('?error=forbidden')
    const user = userEvent.setup()
    // Click Google tab to make it active and render OAuthButtons
    await user.click(screen.getByText('login.tabGoogle'))
    const oauthBtn = await screen.findByTestId('oauth-buttons')
    expect(oauthBtn).toHaveAttribute('data-error', 'true')
  })

  it('does not pass error to OAuthButtons when no error param and GitHub tab is active', async () => {
    renderPage()
    const user = userEvent.setup()
    await user.click(screen.getByText('login.tabGithub'))
    const oauthBtn = await screen.findByTestId('oauth-buttons')
    expect(oauthBtn).toHaveAttribute('data-error', 'false')
  })
})
