import { Link } from 'react-router-dom'

import { cartCount, cartTotal, useCart } from '@/features/cart/store'
import { useAuth } from '@/features/auth/store'
import { yuanWithSymbol } from '@/shared/lib/money'

export function CartPage() {
  const lines = useCart((state) => state.lines)
  const stallName = useCart((state) => state.stallName)
  const minOrderCents = useCart((state) => state.minOrderCents)
  const increase = useCart((state) => state.increase)
  const decrease = useCart((state) => state.decrease)
  const clear = useCart((state) => state.clear)
  const status = useAuth((state) => state.status)

  const total = cartTotal(lines)

  if (lines.length === 0) {
    return (
      <section className="rounded-card bg-surface p-10 text-center">
        <p className="text-sm text-ink-500">购物车还是空的</p>
        <Link to="/stalls" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
          去挑点吃的 →
        </Link>
      </section>
    )
  }

  return (
    <section className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold tracking-tight">购物车</h1>
        <button type="button" className="text-xs text-ink-500 hover:text-red-600" onClick={clear}>
          清空
        </button>
      </header>

      <div className="rounded-card bg-surface p-4 shadow-sm">
        <p className="text-sm text-ink-500">{stallName}</p>
        <ul className="mt-3 divide-y divide-ink-300/60">
          {lines.map((line) => (
            <li key={line.key} className="flex items-start justify-between gap-4 py-3">
              <div className="min-w-0">
                <p className="font-medium">{line.name}</p>
                {line.optionNames.length > 0 ? (
                  <p className="mt-0.5 text-xs text-ink-500">{line.optionNames.join(' · ')}</p>
                ) : null}
                <p className="mt-1 text-sm text-brand-600">
                  {yuanWithSymbol(line.unitPriceCents)}
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  className="h-7 w-7 rounded-full border border-ink-300 text-sm"
                  onClick={() => decrease(line.key)}
                >
                  −
                </button>
                <span className="w-6 text-center text-sm">{line.quantity}</span>
                <button
                  type="button"
                  className="h-7 w-7 rounded-full border border-ink-300 text-sm"
                  onClick={() => increase(line.key)}
                >
                  +
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-center justify-between rounded-card bg-surface p-4 shadow-sm">
        <div>
          <p className="text-xs text-ink-500">共 {cartCount(lines)} 件</p>
          <p className="text-lg font-semibold text-brand-600">{yuanWithSymbol(total)}</p>
          {total < minOrderCents ? (
            <p className="mt-1 text-xs text-amber-600">
              还差 {yuanWithSymbol(minOrderCents - total)} 起送（配送单需要）
            </p>
          ) : null}
        </div>

        <Link
          to={status === 'authed' ? '/checkout' : '/login?next=/checkout'}
          className="rounded-pill bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          {status === 'authed' ? '去结算' : '登录后结算'}
        </Link>
      </div>
    </section>
  )
}