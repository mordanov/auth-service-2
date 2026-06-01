import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage.jsx'
import AdminPage from './pages/AdminPage.jsx'
import { verifyToken } from './api/authApi.js'

function AdminGuard({ user, setUser, loading }) {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && !user) {
      const redirect = encodeURIComponent(window.location.href)
      navigate(`/login?redirect=${redirect}`, { replace: true })
    }
  }, [user, loading, navigate])

  if (loading) return null

  if (!user) return null

  if (user.role !== 'admin') {
    return <Navigate to="/login" replace />
  }

  return <AdminPage user={user} setUser={setUser} />
}

function AppRoutes() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const location = useLocation()

  useEffect(() => {
    // Skip auth check on /login — avoid redirect loop
    if (location.pathname === '/login') {
      setLoading(false)
      return
    }

    verifyToken()
      .then((data) => {
        setUser(data)
        setLoading(false)
      })
      .catch(() => {
        setUser(null)
        setLoading(false)
        const redirect = encodeURIComponent(window.location.href)
        window.location.href = `/login?redirect=${redirect}`
      })
  }, [location.pathname])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage user={user} setUser={setUser} />} />
      <Route
        path="/admin"
        element={
          <AdminGuard user={user} setUser={setUser} loading={loading} />
        }
      />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
