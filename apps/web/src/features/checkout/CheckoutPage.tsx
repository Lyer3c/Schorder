import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/features/auth/store'
import { cartTotal, useCart } from '@/features/cart/store'
import { createOrder, payOrder, previewOrder, type CreateOrderPayload } from '@/features/orders/api'
import { ApiError } from '@/shared/api/client'
import { yuanWithSymbol } from '@/shared/lib/money'

export function CheckoutPage() {
  const navigate = useNavigate()
  const cart = useCart()
  const user = useAuth((state) => state.user)
  const csrfToken = useAuth((state) => state.csrfToken)

  const [fulfillment, setFulfillment] = useState<'pickup' | 'delivery'>('pickup')
  const [contactName, setContactName] = useState(user?.nickname ?? '')
  const [contactPhone, setContactPhone] = useState(user?.phone ?? '')
  const [remark, setRemark] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const items = useMemo(
    () =>
      cart.lines.map((line) => ({
        dishId: line.dishId,
        quantity: line.quantity,
        optionIds: line.optionIds,
      })),
    [cart.lines],
  )

  const preview = useQuery({
    queryKey: ['preview', cart.stallId, fulfillment, items],
    queryFn: () =>
      previewOrder(
        {
          stallId: cart.stallId ?? '',
          fulfillmentType: fulfillment,
          items,
        },
        csrfToken ?? '',
      ),
    enabled: Boolean(csrfToken && cart.stallId && items.length > 0),
    retry: false,
  })

  // 空购物车直接回到列表，避免停在无效页面
  useEffect(() => {
    if (cart.lines.length === 0) navigate('/cart', { replace: true })
  }, [cart.lines.length, navigate])

  const submit = async () => {
    if (!csrfToken || !cart.stallId) return
    setError(null)
    setPending(true)
    try {
      const payload: CreateOrderPayload = {
        stallId: cart.stallId,
        fulfillmentType: fulfillment,
        items,
        contactName,
        contactPhone,
        remark: remark || undefined,
        idempotencyKey: crypto.randomUUID(),
      }
      const order = await createOrder(payload, csrfToken)
      const paid = await payOrder(order.id, csrfToken)
      cart.clear()
      navigate(`/orders/${paid.id}`, { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : '下单失败，请稍后重试')
    } finally {
      setPending(false)
    }
  }

  const amount = preview.data?.amount
  const estimated = preview.data?.estimatedMinutes ?? 15

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold tracking-tight">确认订单</h1>

      <div className="rounded-card bg-surface p-4 shadow-sm">
        <p className="text-sm text-ink-500">{cart.stallName}</p>
        <ul className="mt-2 divide-y divide-ink-300/60 text-sm">
          {cart.lines.map((line) => (
            <li key={line.key} className="flex justify-between py-2">
              <span>
                {line.name}
                {line.optionNames.length > 0 ? (
                  <span className="text-xs text-ink-500">（{line.optionNames.join('·')}）</span>
                ) : null}
                <span className="text-ink-500"> × {line.quantity}</span>
              </span>
              <span>{yuanWithSymbol(line.unitPriceCents * line.quantity)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-card bg-surface p-4 shadow-sm">
        <div className="flex gap-2">
          {(['pickup', 'delivery'] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setFulfillment(value)}
              className={[
                'rounded-pill px-3 py-1.5 text-sm',
                fulfillment === value ? 'bg-brand-500 text-white' : 'bg-canvas text-ink-700',
              ].join(' ')}
            >
              {value === 'pickup' ? '到店自提' : '送到宿舍'}
            </button>
          ))}
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-xs text-ink-500">联系人</span>
            <input
              className="w-full rounded-md border border-ink-300 px-3 py-2"
              value={contactName}
              onChange={(event) => setContactName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-xs text-ink-500">联系电话</span>
            <input
              className="w-full rounded-md border border-ink-300 px-3 py-2"
              value={contactPhone}
              onChange={(event) => setContactPhone(event.target.value)}
            />
          </label>
        </div>

        <label className="mt-3 block text-sm">
          <span className="mb-1 block text-xs text-ink-500">备注（可选）</span>
          <input
            className="w-full rounded-md border border-ink-300 px-3 py-2"
            value={remark}
            maxLength={100}
            onChange={(event) => setRemark(event.target.value)}
            placeholder="少辣、不要香菜…"
          />
        </label>

        {fulfillment === 'delivery' ? (
          <p className="mt-3 text-xs text-amber-600">
            地址簿在后续里程碑接入；当前配送单只做金额校验（起送价与配送费）。
          </p>
        ) : null}
      </div>

      <div className="rounded-card bg-surface p-4 shadow-sm">
        {preview.isError ? (
          <p className="text-sm text-red-600">
            {preview.error instanceof ApiError ? preview.error.message : '试算失败'}
          </p>
        ) : null}

        <dl className="space-y-1 text-sm">
          <Row label="商品金额" value={yuanWithSymbol(amount?.itemsAmountCents ?? cartTotal(cart.lines))} />
          <Row label="打包费" value={yuanWithSymbol(amount?.packingFeeCents ?? 0)} />
          <Row label="配送费" value={yuanWithSymbol(amount?.deliveryFeeCents ?? 0)} />
          <div className="flex justify-between border-t border-ink-300/60 pt-2 font-medium">
            <dt>合计</dt>
            <dd className="text-brand-600">
              {yuanWithSymbol(amount?.payableCents ?? cartTotal(cart.lines))}
            </dd>
          </div>
        </dl>

        <p className="mt-2 text-xs text-ink-500">预计 {estimated} 分钟出餐</p>

        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

        <button
          type="button"
          disabled={pending || preview.isPending || preview.isError}
          onClick={() => void submit()}
          className="mt-4 w-full rounded-pill bg-brand-500 py-2.5 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-60"
        >
          {pending ? '提交中…' : '提交并支付（模拟）'}
        </button>
      </div>
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