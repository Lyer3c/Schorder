import { useEffect } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { logout } from '@/features/auth/api'
import { useAuth } from '@/features/auth/store'
import { cartCount, useCart } from '@/features/cart/store'

const navItems = [
  { to: '/', label: '首页', end: true },
  { to: '/stalls', label: '档口', end: false },
  { to: '/orders', label: '订单', end: false },
  { to: '/merchant', label: '商家', end: false },
  { to: '/admin', label: '管理', end: false },
]

export function RootLayout() {
  const navigate = useNavigate()
  const status = useAuth((state) => state.status)
  const user = useAuth((state) => state.user)
  const csrfToken = useAuth((state) => state.csrfToken)
  const refresh = useAuth((state) => state.refresh)
  const clear = useAuth((state) => state.clear)
  const lines = useCart((state) => state.lines)

  // 启动时用 Cookie 换一次会话摘要（同时也是 CSRF 令牌的来源）
  useEffect(() => {
    if (status === 'unknown') void refresh()
  }, [status, refresh])

  const onLogout = async () => {
    if (csrfToken) {
      try {
        await logout(csrfToken)
      } catch {
        // 令牌可能已过期，忽略即可
      }
    }
    clear()
    navigate('/')
  }

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-10 border-b border-ink-300/60 bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-[1100px] items-center gap-4 px-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Schorder
            <span className="ml-2 align-middle text-xs font-normal text-ink-500">校园点餐</span>
          </Link>

          <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    'shrink-0 rounded-pill px-3 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'bg-brand-50 font-medium text-brand-600'
                      : 'text-ink-700 hover:bg-ink-300/30',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-3">
            <Link to="/cart" className="relative text-sm text-ink-700 hover:text-brand-600">
              购物车
              {cartCount(lines) > 0 ? (
                <span className="ml-1 rounded-full bg-brand-500 px-1.5 py-0.5 text-xs text-white">
                  {cartCount(lines)}
                </span>
              ) : null}
            </Link>

            {status === 'authed' && user ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-ink-500">{user.nickname}</span>
                <button
                  type="button"
                  onClick={() => void onLogout()}
                  className="text-ink-500 hover:text-brand-600"
                >
                  退出
                </button>
              </div>
            ) : (
              <Link to="/login" className="text-sm text-brand-600 hover:underline">
                登录
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1100px] flex-1 px-4 py-6">
        <Outlet />
      </main>

      <footer className="border-t border-ink-300/60 px-4 py-4 text-center text-xs text-ink-500">
        Schorder · 演示环境，不产生真实交易
      </footer>
    </div>
  )
}