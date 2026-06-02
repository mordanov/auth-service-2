import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Override the global i18next mock for this test to track changeLanguage
const mockChangeLanguage = vi.fn()
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: {
      language: 'en',
      changeLanguage: mockChangeLanguage,
    },
  }),
}))

// Also stub localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: (k) => store[k] ?? null,
    setItem: (k, v) => { store[k] = String(v) },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

import LanguageSwitcher from '../src/components/LanguageSwitcher.jsx'

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  it('renders RU and EN buttons', () => {
    render(<LanguageSwitcher />)
    expect(screen.getByLabelText('Switch to Russian')).toBeInTheDocument()
    expect(screen.getByLabelText('Switch to English')).toBeInTheDocument()
  })

  it('clicking EN calls i18next.changeLanguage with "en"', async () => {
    const user = userEvent.setup()
    render(<LanguageSwitcher />)
    await user.click(screen.getByLabelText('Switch to English'))
    expect(mockChangeLanguage).toHaveBeenCalledWith('en')
  })

  it('clicking RU calls i18next.changeLanguage with "ru"', async () => {
    const user = userEvent.setup()
    render(<LanguageSwitcher />)
    await user.click(screen.getByLabelText('Switch to Russian'))
    expect(mockChangeLanguage).toHaveBeenCalledWith('ru')
  })

  it('persists selected language to localStorage', async () => {
    const user = userEvent.setup()
    render(<LanguageSwitcher />)
    await user.click(screen.getByLabelText('Switch to English'))
    expect(localStorageMock.getItem('i18nextLng')).toBe('en')
  })
})
