import React, { useState } from 'react'
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Chip,
} from '@heroui/react'
import { useTranslation } from 'react-i18next'
import { patchUser } from '../api/authApi.js'
import AppAccessCheckboxes from './AppAccessCheckboxes.jsx'

export default function UserTable({ users, onUsersChange }) {
  const { t } = useTranslation()
  const [expandedUserId, setExpandedUserId] = useState(null)
  const [blockingId, setBlockingId] = useState(null)
  const [blockError, setBlockError] = useState(null)

  async function handleToggleBlock(user) {
    setBlockingId(user.id)
    setBlockError(null)
    try {
      const updated = await patchUser(user.id, { is_active: !user.is_active })
      onUsersChange((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: updated.is_active } : u))
      )
    } catch {
      setBlockError(t('admin.error_unknown'))
    } finally {
      setBlockingId(null)
    }
  }

  function toggleExpand(userId) {
    setExpandedUserId((prev) => (prev === userId ? null : userId))
  }

  // Build flat rows — one main row per user, plus optional expanded row after it
  const rows = users.flatMap((user) => {
    const mainRow = (
      <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
        <TableCell>{user.username}</TableCell>
        <TableCell>{user.email || '—'}</TableCell>
        <TableCell>{user.role}</TableCell>
        <TableCell>
          <Chip
            color={user.is_active ? 'success' : 'danger'}
            variant="flat"
            size="sm"
          >
            {user.is_active ? t('admin.status_active') : t('admin.status_blocked')}
          </Chip>
        </TableCell>
        <TableCell>
          <div className="flex gap-2">
            <Button
              size="sm"
              color={user.is_active ? 'danger' : 'success'}
              variant="flat"
              isLoading={blockingId === user.id}
              onPress={() => handleToggleBlock(user)}
              aria-label={
                user.is_active
                  ? `${t('admin.btn_block')} ${user.username}`
                  : `${t('admin.btn_unblock')} ${user.username}`
              }
            >
              {user.is_active ? t('admin.btn_block') : t('admin.btn_unblock')}
            </Button>
            <Button
              size="sm"
              variant="flat"
              onPress={() => toggleExpand(user.id)}
              aria-expanded={expandedUserId === user.id}
              aria-controls={`apps-${user.id}`}
              aria-label={`${t('admin.btn_app_access')} ${user.username}`}
            >
              {t('admin.btn_app_access')}
            </Button>
          </div>
        </TableCell>
      </TableRow>
    )

    if (expandedUserId !== user.id) return [mainRow]

    const expandedRow = (
      <TableRow key={`${user.id}-apps`}>
        <TableCell id={`apps-${user.id}`}>
          <AppAccessCheckboxes userId={user.id} />
        </TableCell>
        <TableCell> </TableCell>
        <TableCell> </TableCell>
        <TableCell> </TableCell>
        <TableCell> </TableCell>
      </TableRow>
    )
    return [mainRow, expandedRow]
  })

  const columns = [
    { key: 'username', label: t('admin.col_username') },
    { key: 'email', label: t('admin.col_email') },
    { key: 'role', label: t('admin.col_role') },
    { key: 'status', label: t('admin.col_status') },
    { key: 'actions', label: t('admin.col_actions') },
  ]

  return (
    <div>
      {blockError && (
        <p role="alert" className="text-danger text-sm mb-2">
          {blockError}
        </p>
      )}
      <Table aria-label={t('admin.users_table')} removeWrapper>
        <TableHeader columns={columns}>
          {(col) => <TableColumn key={col.key}>{col.label}</TableColumn>}
        </TableHeader>
        <TableBody emptyContent={t('admin.loading')}>
          {rows}
        </TableBody>
      </Table>
    </div>
  )
}
