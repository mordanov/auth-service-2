import React from 'react'
import { Button, ButtonGroup } from '@heroui/react'
import { useTranslation } from 'react-i18next'

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const current = i18n.language?.startsWith('ru') ? 'ru' : 'en'

  function switchTo(lang) {
    i18n.changeLanguage(lang)
    localStorage.setItem('i18nextLng', lang)
  }

  return (
    <ButtonGroup size="sm" variant="flat" aria-label="Language switcher">
      <Button
        onPress={() => switchTo('ru')}
        color={current === 'ru' ? 'primary' : 'default'}
        aria-pressed={current === 'ru'}
        aria-label="Switch to Russian"
      >
        {t('lang.ru')}
      </Button>
      <Button
        onPress={() => switchTo('en')}
        color={current === 'en' ? 'primary' : 'default'}
        aria-pressed={current === 'en'}
        aria-label="Switch to English"
      >
        {t('lang.en')}
      </Button>
    </ButtonGroup>
  )
}
