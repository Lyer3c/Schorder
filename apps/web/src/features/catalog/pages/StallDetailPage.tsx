import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { fetchStallDetail, type Dish, type DishOptionGroup } from '@/features/catalog/api'
import { yuanWithSymbol } from '@/shared/lib/money'

const WEEKDAY_LABEL = ['一', '二', '三', '四', '五', '六', '日']

export function StallDetailPage() {
  const { stallId } = useParams<{ stallId: string }>()

  const detail = useQuery({
    queryKey: ['stall', stallId],
    queryFn: () => fetchStallDetail(stallId ?? ''),
    enabled: Boolean(stallId),
    retry: false,
  })

  if (detail.isPending) {
    return <div className="h-40 animate-pulse rounded-card bg-ink-300/25" />
  }

  if (detail.isError) {
    return (
      <section className="rounded-card bg-surface p-10 text-center">
        <p className="text-sm text-ink-500">
          {detail.error instanceof Error ? detail.error.message : '档口不存在'}
        </p>
        <Link to="/stalls" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
          返回档口列表
        </Link>
      </section>
    )
  }

  const stall = detail.data

  return (
    <section className="space-y-4">
      <Link to="/stalls" className="text-sm text-ink-500 hover:text-brand-600">
        ← 返回列表
      </Link>

      <header className="rounded-card bg-surface p-5 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{stall.name}</h1>
            <p className="mt-1 text-sm text-ink-500">{stall.description}</p>
          </div>
          <span
            className={[
              'shrink-0 rounded-pill px-2 py-0.5 text-xs',
              stall.isOpen ? 'bg-brand-50 text-brand-600' : 'bg-ink-300/40 text-ink-700',
            ].join(' ')}
          >
            {stall.isOpen ? '营业中' : (stall.opensAt ?? '休息中')}
          </span>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <Stat label="评分" value={stall.rating > 0 ? stall.rating.toFixed(1) : '暂无'} />
          <Stat label="月售" value={`${stall.monthlySales} 单`} />
          <Stat label="起送" value={yuanWithSymbol(stall.minOrderCents)} />
          <Stat label="配送费" value={yuanWithSymbol(stall.deliveryFeeCents)} />
        </dl>

        {stall.notice ? (
          <p className="mt-4 rounded-md bg-brand-50 px-3 py-2 text-xs text-brand-600">
            公告：{stall.notice}
          </p>
        ) : null}

        <p className="mt-3 text-xs text-ink-500">
          营业时间：
          {stall.businessHours
            .filter((hour) => hour.weekday === 1)
            .map((hour) => `${hour.openTime}-${hour.closeTime}`)
            .join(' / ') || '未设置'}
          ｜ 预计 {stall.estimatedMinutes} 分钟出餐
        </p>
      </header>

      {stall.menuGroups.length === 0 ? (
        <p className="rounded-card bg-surface p-10 text-center text-sm text-ink-500">
          这家档口还没有上架菜品
        </p>
      ) : null}

      <div className="space-y-4">
        {stall.menuGroups.map((group) => (
          <div key={group.id} className="rounded-card bg-surface p-4 shadow-sm">
            <h2 className="text-sm font-medium text-ink-700">{group.name}</h2>
            <ul className="mt-3 divide-y divide-ink-300/60">
              {group.dishes.map((dish) => (
                <li key={dish.id} className="py-3">
                  <DishRow dish={dish} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <p className="pb-4 text-center text-xs text-ink-500">
        加购与下单将在 M2 接入；当前只做浏览。
      </p>
    </section>
  )
}

function DishRow({ dish }: { dish: Dish }) {
  const soldOut = dish.status === 'sold_out' || dish.stock <= 0

  return (
    <div className={soldOut ? 'opacity-55' : ''}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-medium">
            {dish.name}
            {soldOut ? (
              <span className="ml-2 rounded-pill bg-ink-300/50 px-2 py-0.5 text-xs text-ink-700">
                售罄
              </span>
            ) : null}
          </p>
          {dish.description ? (
            <p className="mt-0.5 text-xs text-ink-500">{dish.description}</p>
          ) : null}
          {dish.optionGroups.length > 0 ? (
            <p className="mt-1 text-xs text-ink-500">
              {dish.optionGroups.map((group: DishOptionGroup) => group.name).join(' · ')}
            </p>
          ) : null}
        </div>
        <span className="shrink-0 text-sm font-medium text-brand-600">
          {yuanWithSymbol(dish.priceCents)}
        </span>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-ink-500">{label}</dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
    </div>
  )
}

/** 保留给 M2 显示规格：目前只在详情页列出组名，不渲染选项按钮。 */
export { WEEKDAY_LABEL }