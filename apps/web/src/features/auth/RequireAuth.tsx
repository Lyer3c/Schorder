import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '@/features/auth/store'

/** 未登录时送登录页，并带上回跳地址。真正的权限判定仍在后端。 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const status = useAuth((state) => state.status)
  const location = useLocation()

  if (status === 'unknown') {
    return <div className="h-24 animate-pulse rounded-card bg-ink-300/25" />
  }

  if (status === 'guest') {
    const next = encodeURIComponent(location.pathname)
    return <Navigate to={`/login?next=${next}`} replace />
  }

  return <>{children}</>
}