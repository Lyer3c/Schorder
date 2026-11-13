import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { useAuth } from '@/features/auth/store'
import { fetchOrder, payOrder } from '@/features/orders/api'
import { STATUS_LABEL } from '@/features/orders/OrdersPage'
import { ApiError } from '@/shared/api/client'
import { yuanWithSymbol } from '@/shared/lib/money'

export function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const queryClient = useQueryClient()
  const csrfToken = useAuth((state) => state.csrfToken)

  const order = useQuery({
    queryKey: ['order', orderId],
    queryFn: () => fetchOrder(orderId ?? ''),
    enabled: Boolean(orderId),
    retry: false,
  })

  const pay = useMutation({
    mutationFn: () => payOrder(orderId ?? '', csrfToken ?? ''),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['order', orderId] })
      void queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })

  if (order.isPending) {
    return <div className="h-40 animate-pulse rounded-card bg-ink-300/25" />
  }

  if (order.isError) {
    return (
      <section className="rounded-card bg-surface p-10 text-center">
        <p className="text-sm text-ink-500">
          {order.error instanceof ApiError ? order.error.message : '订单不存在'}
        </p>
        <Link to="/orders" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
          返回订单列表
        </Link>
      </section>
    )
  }

  const data = order.data

  return (
    <section className="space-y-4">
      <Link to="/orders" className="text-sm text-ink-500 hover:text-brand-600">
        ← 我的订单
      </Link>

      <header className="rounded-card bg-surface p-5 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">{data.stallName}</h1>
            <p className="mt-1 text-xs text-ink-500">订单号 {data.orderNo}</p>
          </div>
          <span className="rounded-pill bg-brand-50 px-2 py-0.5 text-xs text-brand-600">
            {STATUS_LABEL[data.status] ?? data.status}
          </span>
        </div>

        <p className="mt-3 text-xs text-ink-500">
          {data.fulfillmentType === 'pickup' ? '到店自提' : '配送到宿舍'} · 联系人{' '}
          {data.contactName} {data.contactPhone}
        </p>
        {data.remark ? (
          <p className="mt-1 text-xs text-ink-500">备注：{data.remark}</p>
        ) : null}
      </header>

      <div className="rounded-card bg-surface p-4 shadow-sm">
        <ul className="divide-y divide-ink-300/60 text-sm">
          {data.items.map((item) => (
            <li key={`${item.dishId}-${item.options.map((o) => o.id).join(',')}`} className="py-2">
              <div className="flex justify-between">
                <span>
                  {item.dishName}
                  <span className="text-ink-500"> × {item.quantity}</span>
                </span>
                <span>{yuanWithSymbol(item.lineAmountCents)}</span>
              </div>
              {item.options.length > 0 ? (
                <p className="mt-0.5 text-xs text-ink-500">
                  {item.options.map((option) => option.name).join(' · ')}
                </p>
              ) : null}
            </li>
          ))}
        </ul>

        <dl className="mt-3 space-y-1 border-t border-ink-300/60 pt-3 text-sm">
          <Row label="商品金额" value={yuanWithSymbol(data.amount.itemsAmountCents)} />
          <Row label="打包费" value={yuanWithSymbol(data.amount.packingFeeCents)} />
          <Row label="配送费" value={yuanWithSymbol(data.amount.deliveryFeeCents)} />
          <div className="flex justify-between pt-1 font-medium">
            <dt>合计</dt>
            <dd className="text-brand-600">{yuanWithSymbol(data.amount.payableCents)}</dd>
          </div>
        </dl>
      </div>

      {pay.isError ? (
        <p className="text-sm text-red-600">
          {pay.error instanceof ApiError ? pay.error.message : '支付失败'}
        </p>
      ) : null}

      {data.canPay ? (
        <button
          type="button"
          disabled={pay.isPending}
          onClick={() => pay.mutate()}
          className="w-full rounded-pill bg-brand-500 py-2.5 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-60"
        >
          {pay.isPending ? '支付中…' : '立即支付（模拟）'}
        </button>
      ) : null}

      <p className="pb-4 text-center text-xs text-ink-500">
        下单 {data.createdAt.slice(0, 16).replace('T', ' ')}
        {data.paidAt ? ` · 支付 ${data.paidAt.slice(0, 16).replace('T', ' ')}` : ''}
      </p>
    </section>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-ink-700">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}