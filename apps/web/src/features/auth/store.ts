import { create } from 'zustand'

import { fetchSession, type SessionData, type SessionUser } from '@/features/auth/api'

type AuthStatus = 'unknown' | 'authed' | 'guest'

interface AuthState {
  status: AuthStatus
  user: SessionUser | null
  csrfToken: string | null
  refresh: () => Promise<void>
  setSession: (session: SessionData) => void
  clear: () => void
}

/**
 * 认证状态只放内存：CSRF 令牌刻意不落 localStorage。
 * 会话本身靠 HttpOnly Cookie，刷新页面用 /auth/session 重新取回。
 */
export const useAuth = create<AuthState>((set) => ({
  status: 'unknown',
  user: null,
  csrfToken: null,

  refresh: async () => {
    try {
      const session = await fetchSession()
      set({ status: 'authed', user: session.user, csrfToken: session.csrfToken })
    } catch {
      set({ status: 'guest', user: null, csrfToken: null })
    }
  },

  setSession: (session) =>
    set({ status: 'authed', user: session.user, csrfToken: session.csrfToken }),

  clear: () => set({ status: 'guest', user: null, csrfToken: null }),
}))