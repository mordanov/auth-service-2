import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import OAuthButtons from '../src/components/OAuthButtons.jsx'

describe('OAuthButtons (no provider — shows all)', () => {
  it('renders both Google and GitHub buttons when no provider given', () => {
    render(<OAuthButtons />)
    expect(screen.getByLabelText('login.google_button')).toBeInTheDocument()
    expect(screen.getByLabelText('login.github_button')).toBeInTheDocument()
  })

  it('shows forbidden error when error prop is true', () => {
    render(<OAuthButtons error={true} />)
    expect(screen.getByRole('alert')).toHaveTextContent('login.error_forbidden')
  })

  it('does not show error when error prop is false', () => {
    render(<OAuthButtons error={false} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('OAuthButtons (provider=google)', () => {
  it('renders only the Google button', () => {
    render(<OAuthButtons provider="google" />)
    expect(screen.getByLabelText('login.google_button')).toBeInTheDocument()
    expect(screen.queryByLabelText('login.github_button')).not.toBeInTheDocument()
  })

  it('Google button links to /api/auth/google', () => {
    render(<OAuthButtons provider="google" />)
    expect(screen.getByLabelText('login.google_button')).toHaveAttribute('href', '/api/auth/google')
  })
})

describe('OAuthButtons (provider=github)', () => {
  it('renders only the GitHub button', () => {
    render(<OAuthButtons provider="github" />)
    expect(screen.getByLabelText('login.github_button')).toBeInTheDocument()
    expect(screen.queryByLabelText('login.google_button')).not.toBeInTheDocument()
  })

  it('GitHub button links to /api/auth/github', () => {
    render(<OAuthButtons provider="github" />)
    expect(screen.getByLabelText('login.github_button')).toHaveAttribute('href', '/api/auth/github')
  })
})
