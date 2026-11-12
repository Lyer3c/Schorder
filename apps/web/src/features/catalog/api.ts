import type { components } from '@schorder/contract'

import { apiRequest, apiRequestWithMeta } from '@/shared/api/client'

export type Category = components['schemas']['CategoryOut']
export type StallSummary = components['schemas']['StallSummaryOut']
export type StallDetail = components['schemas']['StallDetailOut']
export type Dish = components['schemas']['DishOut']
export type MenuGroup = components['schemas']['MenuGroupOut']
export type PageMeta = components['schemas']['PageMeta']
export type DishOptionGroup = components['schemas']['DishOptionGroupOut']

export type StallSort = 'recommended' | 'sales' | 'rating' | 'min_order'

export interface StallQuery {
  categoryId?: string | undefined
  keyword?: string | undefined
  sort?: StallSort | undefined
  openNow?: boolean | undefined
  limit?: number | undefined
  cursor?: string | null | undefined
}

export interface StallPage {
  items: StallSummary[]
  nextCursor: string | null
}

const SORT_LABEL: Record<StallSort, string> = {
  recommended: '推荐',
  sales: '销量',
  rating: '评分',
  min_order: '起送价',
}

export const SORT_OPTIONS = SORT_LABEL

export function fetchCategories(): Promise<Category[]> {
  return apiRequest<Category[]>('/api/v1/categories')
}

export async function fetchStalls(query: StallQuery = {}): Promise<StallPage> {
  const params = new URLSearchParams()
  if (query.categoryId) params.set('categoryId', query.categoryId)
  if (query.keyword) params.set('keyword', query.keyword)
  if (query.sort) params.set('sort', query.sort)
  if (query.openNow) params.set('openNow', 'true')
  params.set('limit', String(query.limit ?? 20))
  if (query.cursor) params.set('cursor', query.cursor)

  const result = await apiRequestWithMeta<StallSummary[], PageMeta>(
    `/api/v1/stalls?${params.toString()}`,
  )
  return { items: result.data, nextCursor: result.meta?.nextCursor ?? null }
}

export function fetchStallDetail(id: string): Promise<StallDetail> {
  return apiRequest<StallDetail>(`/api/v1/stalls/${id}`)
}