import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { fetchOrders } from '@/features/orders/api'
import { yuanWithSymbol } from '@/shared/lib/money'

export const STATUS_LABEL: Record<string, string> = {
  pending_payment: '待支付',
  paid: '已支付',
  accepted: '已接单',
  preparing: '制作中',
  ready: '待取餐',
  delivering: '配送中',
  completed: '已完成',
  cancelled: '已取消',
}

const FILTERS = [
  { value: undefined, label: '全部' },
  { value: 'pending_payment', label: '待支付' },
  { value: 'paid', label: '已支付' },
  { value: 'completed', label: '已完成' },
] as const

export function OrdersPage() {
  const [status, setStatus] = useState<string | undefined>(undefined)

  const orders = useQuery({
    queryKey: ['orders', status ?? 'all'],
    queryFn: () => fetchOrders(status),
  })

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold tracking-tight">我的订单</h1>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((item) => (
          <button
            key={item.label}
            type="button"
            onClick={() => setStatus(item.value)}
            className={[
              'rounded-pill px-3 py-1.5 text-sm',
              status === item.value ? 'bg-brand-500 text-white' : 'bg-surface text-ink-700',
            ].join(' ')}
          >
            {item.label}
          </button>
        ))}
      </div>

      {orders.isPending ? (
        <div className="h-24 animate-pulse rounded-card bg-ink-300/25" />
      ) : null}

      {orders.isError ? (
        <p className="rounded-card bg-surface p-6 text-sm text-red-600">加载失败</p>
      ) : null}

      {orders.data && orders.data.items.length === 0 ? (
        <p className="rounded-card bg-surface p-10 text-center text-sm text-ink-500">
          还没有订单
        </p>
      ) : null}

      <ul className="space-y-3">
        {orders.data?.items.map((order) => (
          <li key={order.id}>
            <Link
              to={`/orders/${order.id}`}
              className="block rounded-card bg-surface p-4 shadow-sm hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{order.stallName}</p>
                  <p className="mt-1 text-xs text-ink-500">
                    {order.items.length} 件 · {order.orderNo}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span className="rounded-pill bg-brand-50 px-2 py-0.5 text-xs text-brand-600">
                    {STATUS_LABEL[order.status] ?? order.status}
                  </span>
                  <p className="mt-1 text-sm font-medium">
                    {yuanWithSymbol(order.amount.payableCents)}
                  </p>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}