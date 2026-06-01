import React, { useState } from 'react'
import { Input, Button } from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { login } from '../api/authApi.js'

export default function LoginForm({ onSuccess, redirectUrl }) {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!username || !password) return
    setError(null)
    setLoading(true)
    try {
      await login(username, password)
      onSuccess(redirectUrl || '/')
    } catch (err) {
      if (err.status === 401) {
        setError(t('login.error_invalid_credentials'))
      } else if (err.status === 403) {
        setError(t('login.error_forbidden'))
      } else {
        setError(t('login.error_unknown'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="flex flex-col gap-4">
        <Input
          label={t('login.username')}
          placeholder={t('login.username_placeholder')}
          value={username}
          onValueChange={setUsername}
          autoComplete="username"
          isRequired
          aria-label={t('login.username')}
        />
        <Input
          label={t('login.password')}
          placeholder={t('login.password_placeholder')}
          type="password"
          value={password}
          onValueChange={setPassword}
          autoComplete="current-password"
          isRequired
          aria-label={t('login.password')}
        />
        {error && (
          <p role="alert" className="text-danger text-sm">
            {error}
          </p>
        )}
        <Button
          type="submit"
          color="primary"
          isLoading={loading}
          isDisabled={!username || !password}
          fullWidth
        >
          {t('login.submit')}
        </Button>
      </div>
    </form>
  )
}
