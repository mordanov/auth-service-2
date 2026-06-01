import React from 'react'
import { Card, CardBody, Tabs, Tab } from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { useSearchParams, useNavigate } from 'react-router-dom'
import LoginForm from '../components/LoginForm.jsx'
import OAuthButtons from '../components/OAuthButtons.jsx'
import LanguageSwitcher from '../components/LanguageSwitcher.jsx'

export default function LoginPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const redirectUrl = searchParams.get('redirect') || '/'
  const oauthError = searchParams.get('error') === 'forbidden'

  function handleLoginSuccess(target) {
    // Validate redirect stays within .mainpage.com or is a relative path
    try {
      const url = new URL(target)
      if (url.hostname.endsWith('.mainpage.com') || url.hostname === 'mainpage.com') {
        window.location.href = target
      } else {
        navigate('/', { replace: true })
      }
    } catch {
      // Relative URL
      navigate(target, { replace: true })
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-default-50 p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-end mb-4">
          <LanguageSwitcher />
        </div>
        <Card>
          <CardBody className="p-6">
            <h1 className="text-2xl font-semibold text-center mb-6">
              {t('login.title')}
            </h1>
            <Tabs
              aria-label={t('login.title')}
              fullWidth
              variant="bordered"
            >
              <Tab key="password" title={t('login.tabPassword')}>
                <div className="pt-4">
                  <LoginForm
                    onSuccess={handleLoginSuccess}
                    redirectUrl={redirectUrl}
                  />
                </div>
              </Tab>
              <Tab key="google" title={t('login.tabGoogle')}>
                <div className="pt-4">
                  <OAuthButtons provider="google" error={oauthError} />
                </div>
              </Tab>
              <Tab key="github" title={t('login.tabGithub')}>
                <div className="pt-4">
                  <OAuthButtons provider="github" error={oauthError} />
                </div>
              </Tab>
            </Tabs>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
