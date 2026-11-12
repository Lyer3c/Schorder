import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { fetchCategories, fetchStalls } from '@/features/catalog/api'
import { StallCard } from '@/features/catalog/components/StallCard'
import type { MetaData } from '@/features/home/api'
import { apiRequest } from '@/shared/api/client'
import { queryKeys } from '@/shared/api/queryKeys'

export function HomePage() {
  const meta = useQuery({
    queryKey: queryKeys.meta,
    queryFn: () => apiRequest<MetaData>('/api/v1/meta'),
  })
  const categories = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })
  const recommended = useQuery({
    queryKey: ['stalls', 'home'],
    queryFn: () => fetchStalls({ limit: 4, sort: 'recommended' }),
  })

  return (
    <section className="space-y-6">
      <div className="rounded-card bg-surface p-6 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight">今天想吃点什么？</h1>
        <p className="mt-2 text-sm leading-6 text-ink-500">
          校园内的档口外卖与自提。浏览菜单、挑选菜品，下单在 M2 开放。
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {categories.data?.map((category) => (
            <Link
              key={category.id}
              to={`/stalls?categoryId=${category.id}`}
              className="rounded-pill bg-brand-50 px-3 py-1.5 text-sm text-brand-600 hover:bg-brand-100"
            >
              {category.name}
            </Link>
          ))}
          {categories.isPending ? <span className="text-sm text-ink-500">分类加载中…</span> : null}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-lg font-medium">推荐档口</h2>
          <Link to="/stalls" className="text-sm text-brand-600 hover:underline">
            查看全部 →
          </Link>
        </div>

        {recommended.isPending ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {[0, 1].map((index) => (
              <div key={index} className="h-24 animate-pulse rounded-card bg-ink-300/25" />
            ))}
          </div>
        ) : null}

        {recommended.isError ? (
          <p className="rounded-card bg-surface p-6 text-sm text-red-600">
            加载失败：{recommended.error instanceof Error ? recommended.error.message : '未知错误'}
          </p>
        ) : null}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {recommended.data?.items.map((stall) => (
            <StallCard key={stall.id} stall={stall} />
          ))}
        </div>
      </div>

      <p className="text-center text-xs text-ink-500">
        {meta.data
          ? `${meta.data.name} v${meta.data.version} · ${meta.data.env}`
          : '后端连接中…'}
      </p>
    </section>
  )
}