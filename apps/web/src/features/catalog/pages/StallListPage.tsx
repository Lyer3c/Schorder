import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import {
  SORT_OPTIONS,
  fetchCategories,
  fetchStalls,
  type StallSort,
} from '@/features/catalog/api'
import { StallCard } from '@/features/catalog/components/StallCard'

export function StallListPage() {
  // 分类放在 URL 里：首页的分类入口可以直接跳过来，链接也能分享
  const [searchParams, setSearchParams] = useSearchParams()
  const categoryId = searchParams.get('categoryId') ?? undefined
  const [sort, setSort] = useState<StallSort>('recommended')
  const [openNow, setOpenNow] = useState(false)

  const selectCategory = (next: string | undefined) => {
    const params = new URLSearchParams(searchParams)
    if (next) {
      params.set('categoryId', next)
    } else {
      params.delete('categoryId')
    }
    setSearchParams(params, { replace: true })
  }

  const categories = useQuery({ queryKey: ['categories'], queryFn: fetchCategories })

  const stalls = useInfiniteQuery({
    queryKey: ['stalls', categoryId ?? 'all', sort, openNow],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => fetchStalls({ categoryId, sort, openNow, cursor: pageParam }),
    getNextPageParam: (last) => last.nextCursor,
  })

  const items = stalls.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <section className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold tracking-tight">全部档口</h1>
        <span className="text-xs text-ink-500">{items.length} 家</span>
      </header>

      <div className="flex flex-wrap gap-2">
        <CategoryChip active={!categoryId} onClick={() => selectCategory(undefined)}>
          全部
        </CategoryChip>
        {categories.data?.map((category) => (
          <CategoryChip
            key={category.id}
            active={categoryId === category.id}
            onClick={() => selectCategory(category.id)}
          >
            {category.name}
          </CategoryChip>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-card bg-surface px-4 py-3 text-sm">
        <label className="flex items-center gap-2 text-ink-700">
          排序
          <select
            className="rounded-md border border-ink-300 bg-surface px-2 py-1"
            value={sort}
            onChange={(event) => setSort(event.target.value as StallSort)}
          >
            {Object.entries(SORT_OPTIONS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-ink-700">
          <input
            type="checkbox"
            checked={openNow}
            onChange={(event) => setOpenNow(event.target.checked)}
          />
          只看营业中
        </label>
      </div>

      {stalls.isPending ? <StallSkeleton /> : null}

      {stalls.isError ? (
        <p className="rounded-card bg-surface p-6 text-sm text-red-600">
          加载失败：{stalls.error instanceof Error ? stalls.error.message : '未知错误'}
        </p>
      ) : null}

      {!stalls.isPending && !stalls.isError && items.length === 0 ? (
        <p className="rounded-card bg-surface p-10 text-center text-sm text-ink-500">
          没有符合条件的档口，试试放宽筛选
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {items.map((stall) => (
          <StallCard key={stall.id} stall={stall} />
        ))}
      </div>

      {stalls.hasNextPage ? (
        <div className="pt-2 text-center">
          <button
            type="button"
            className="rounded-pill border border-ink-300 px-5 py-2 text-sm hover:bg-surface disabled:opacity-50"
            disabled={stalls.isFetchingNextPage}
            onClick={() => void stalls.fetchNextPage()}
          >
            {stalls.isFetchingNextPage ? '加载中…' : '加载更多'}
          </button>
        </div>
      ) : null}
    </section>
  )
}

function CategoryChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-pill px-3 py-1.5 text-sm transition-colors',
        active ? 'bg-brand-500 text-white' : 'bg-surface text-ink-700 hover:bg-brand-50',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

function StallSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {[0, 1, 2, 3].map((index) => (
        <div key={index} className="h-24 animate-pulse rounded-card bg-ink-300/25" />
      ))}
    </div>
  )
}