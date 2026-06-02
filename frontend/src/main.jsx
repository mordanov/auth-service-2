import React from 'react'
import ReactDOM from 'react-dom/client'
import { HeroUIProvider } from '@heroui/react'
import { I18nextProvider } from 'react-i18next'
import i18n from './i18n/index.js'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <I18nextProvider i18n={i18n}>
      <HeroUIProvider>
        <App />
      </HeroUIProvider>
    </I18nextProvider>
  </React.StrictMode>
)
