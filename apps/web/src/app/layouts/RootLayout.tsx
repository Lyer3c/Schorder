import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: '首页', end: true },
  { to: '/stalls', label: '档口', end: false },
  { to: '/merchant', label: '商家', end: false },
  { to: '/admin', label: '管理', end: false },
]

export function RootLayout() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="sticky top-0 z-10 border-b border-ink-300/60 bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-[1100px] items-center gap-6 px-4">
          <span className="text-lg font-semibold tracking-tight">
            Schorder
            <span className="ml-2 align-middle text-xs font-normal text-ink-500">校园点餐</span>
          </span>

          <nav className="flex items-center gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    'rounded-pill px-3 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'bg-brand-50 text-brand-600 font-medium'
                      : 'text-ink-700 hover:bg-ink-300/30',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
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