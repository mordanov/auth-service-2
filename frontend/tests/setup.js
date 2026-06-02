import '@testing-library/jest-dom'
import { vi } from 'vitest'

// ResizeObserver is not in jsdom — stub it globally
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Stub i18next so components render with key strings in tests
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: {
      language: 'en',
      changeLanguage: vi.fn(),
    },
  }),
  I18nextProvider: ({ children }) => children,
  initReactI18next: { type: '3rdParty', init: vi.fn() },
}))
