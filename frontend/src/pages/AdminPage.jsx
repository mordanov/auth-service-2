import React, { useState, useEffect } from 'react'
import { Button, Spinner } from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { getUsers, logout } from '../api/authApi.js'
import UserTable from '../components/UserTable.jsx'
import UserCreateModal from '../components/UserCreateModal.jsx'
import LanguageSwitcher from '../components/LanguageSwitcher.jsx'

export default function AdminPage({ user, setUser }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)

  useEffect(() => {
    fetchUsers()
  }, [])

  async function fetchUsers() {
    setLoading(true)
    setError(null)
    try {
      const data = await getUsers()
      setUsers(data)
    } catch (err) {
      if (err?.status === 403) {
        setError(t('admin.error_forbidden'))
      } else {
        setError(t('admin.error_unknown'))
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleLogout() {
    await logout()
    setUser(null)
    navigate('/login', { replace: true })
  }

  function handleUserCreated(newUser) {
    setUsers((prev) => [...prev, newUser])
    setModalOpen(false)
  }

  return (
    <div className="min-h-screen bg-default-50">
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-default-200">
        <h1 className="text-xl font-semibold">{t('admin.title')}</h1>
        <div className="flex items-center gap-4">
          <LanguageSwitcher />
          <Button variant="flat" onPress={handleLogout} size="sm">
            {t('app.logout')}
          </Button>
        </div>
      </header>

      <main className="p-6">
        {error && (
          <p role="alert" className="text-danger mb-4">
            {error}
          </p>
        )}

        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium">{t('admin.users_table')}</h2>
          <Button
            color="primary"
            onPress={() => setModalOpen(true)}
            aria-label={t('admin.create_user')}
          >
            {t('admin.create_user')}
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12" aria-label={t('admin.loading')}>
            <Spinner />
          </div>
        ) : (
          <UserTable users={users} onUsersChange={setUsers} />
        )}
      </main>

      <UserCreateModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={handleUserCreated}
      />
    </div>
  )
}
