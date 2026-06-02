import React, { useState, useEffect } from 'react'
import { Checkbox, Button, Spinner } from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { getApps, putApps } from '../api/authApi.js'

const APP_NAMES = [
  'budget-site',
  'family-admin-routine',
  'family-archive',
  'family-kitchen-recipes',
  'new-site',
  'portuguese-expenses',
  'reminders-app',
  'servinga-dashboard',
]

export default function AppAccessCheckboxes({ userId }) {
  const { t } = useTranslation()
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    getApps(userId)
      .then(setApps)
      .catch(() => setError(t('admin.error_unknown')))
      .finally(() => setLoading(false))
  }, [userId])

  function toggle(appName) {
    setApps((prev) =>
      prev.map((a) =>
        a.app_name === appName ? { ...a, is_enabled: !a.is_enabled } : a
      )
    )
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const updated = await putApps(userId, apps)
      setApps(updated)
    } catch {
      setError(t('admin.error_unknown'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spinner size="sm" aria-label={t('admin.loading')} />

  return (
    <div className="flex flex-col gap-3 p-2">
      <p className="font-medium text-sm">{t('admin.apps_title')}</p>
      <div className="grid grid-cols-2 gap-2">
        {APP_NAMES.map((name) => {
          const entry = apps.find((a) => a.app_name === name)
          return (
            <Checkbox
              key={name}
              isSelected={entry?.is_enabled ?? false}
              onValueChange={() => toggle(name)}
              aria-label={t(`apps.${name}`, { defaultValue: name })}
            >
              {t(`apps.${name}`, { defaultValue: name })}
            </Checkbox>
          )
        })}
      </div>
      {error && (
        <p role="alert" className="text-danger text-sm">
          {error}
        </p>
      )}
      <Button
        size="sm"
        color="primary"
        onPress={handleSave}
        isLoading={saving}
        aria-label={t('admin.apps_save')}
      >
        {t('admin.apps_save')}
      </Button>
    </div>
  )
}
