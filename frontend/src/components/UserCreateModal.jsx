import React, { useState } from 'react'
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
} from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { createUser } from '../api/authApi.js'

export default function UserCreateModal({ isOpen, onClose, onCreated }) {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  function reset() {
    setUsername('')
    setEmail('')
    setPassword('')
    setError(null)
  }

  function handleClose() {
    reset()
    onClose()
  }

  async function handleSubmit() {
    if (!username) {
      setError(t('admin.error_username_required'))
      return
    }
    if (!password) {
      setError(t('admin.error_password_required'))
      return
    }
    setError(null)
    setLoading(true)
    try {
      const user = await createUser({
        username,
        email: email || null,
        password,
        role: 'user',
      })
      reset()
      onCreated(user)
    } catch (err) {
      if (err.status === 409) {
        setError(t('admin.error_conflict'))
      } else {
        setError(t('admin.error_unknown'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      aria-labelledby="create-user-modal-title"
    >
      <ModalContent>
        <ModalHeader id="create-user-modal-title">
          {t('admin.modal_create_title')}
        </ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-4">
            <Input
              label={t('admin.modal_username')}
              value={username}
              onValueChange={setUsername}
              isRequired
              autoComplete="off"
              aria-label={t('admin.modal_username')}
            />
            <Input
              label={t('admin.modal_email')}
              type="email"
              value={email}
              onValueChange={setEmail}
              autoComplete="off"
              aria-label={t('admin.modal_email')}
            />
            <Input
              label={t('admin.modal_password')}
              type="password"
              value={password}
              onValueChange={setPassword}
              isRequired
              autoComplete="new-password"
              aria-label={t('admin.modal_password')}
            />
            {error && (
              <p role="alert" className="text-danger text-sm">
                {error}
              </p>
            )}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button variant="flat" onPress={handleClose}>
            {t('admin.modal_cancel')}
          </Button>
          <Button color="primary" onPress={handleSubmit} isLoading={loading}>
            {t('admin.modal_submit')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  )
}
