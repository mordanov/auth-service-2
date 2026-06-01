import { useState, useEffect } from 'react'
import { verifyToken } from '../api/authApi.js'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    verifyToken()
      .then((data) => {
        setUser(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err)
        setUser(null)
        setLoading(false)
      })
  }, [])

  return { user, loading, error }
}

// Imperative check — redirects to login on 401, returns user data on 200
export async function checkAuth() {
  try {
    return await verifyToken()
  } catch {
    const redirect = encodeURIComponent(window.location.href)
    window.location.href = `/login?redirect=${redirect}`
    return null
  }
}
