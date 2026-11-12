import { Link } from 'react-router-dom'

import type { StallSummary } from '@/features/catalog/api'
import { yuanWithSymbol } from '@/shared/lib/money'

export function StallCard({ stall }: { stall: StallSummary }) {
  return (
    <Link
      to={`/stalls/${stall.id}`}
      className="block rounded-card bg-surface p-4 shadow-sm transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-medium">{stall.name}</h3>
          <p className="mt-1 text-xs text-ink-500">
            {stall.categoryName} · 月售 {stall.monthlySales}
          </p>
        </div>

        {stall.isOpen ? (
          <span className="shrink-0 rounded-pill bg-brand-50 px-2 py-0.5 text-xs text-brand-600">
            营业中
          </span>
        ) : (
          <span className="shrink-0 rounded-pill bg-ink-300/40 px-2 py-0.5 text-xs text-ink-700">
            {stall.opensAt ?? '休息中'}
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-500">
        <span className="text-brand-600">★ {stall.rating > 0 ? stall.rating.toFixed(1) : '暂无'}</span>
        <span>起送 {yuanWithSymbol(stall.minOrderCents)}</span>
        <span>配送 {yuanWithSymbol(stall.deliveryFeeCents)}</span>
        <span>约 {stall.estimatedMinutes} 分钟</span>
      </div>
    </Link>
  )
}