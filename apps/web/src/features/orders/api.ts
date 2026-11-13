import type { components } from '@schorder/contract'

import { apiRequest, apiRequestWithMeta } from '@/shared/api/client'

export type OrderOut = components['schemas']['OrderOut']
export type PreviewOut = components['schemas']['PreviewOut']
export type PageMeta = components['schemas']['PageMeta']

export interface OrderItemInput {
  dishId: string
  quantity: number
  optionIds: string[]
}

export interface CreateOrderPayload {
  stallId: string
  fulfillmentType: 'pickup' | 'delivery'
  items: OrderItemInput[]
  contactName: string
  contactPhone: string
  tablewareCount?: number | undefined
  remark?: string | undefined
  addressId?: string | undefined
  idempotencyKey: string
}

export function previewOrder(
  payload: Omit<CreateOrderPayload, 'contactName' | 'contactPhone' | 'idempotencyKey'>,
  csrfToken: string,
): Promise<PreviewOut> {
  return apiRequest<PreviewOut>('/api/v1/orders/preview', {
    method: 'POST',
    body: payload,
    csrfToken,
  })
}

export function createOrder(payload: CreateOrderPayload, csrfToken: string): Promise<OrderOut> {
  return apiRequest<OrderOut>('/api/v1/orders', {
    method: 'POST',
    body: payload,
    csrfToken,
  })
}

export function payOrder(orderId: string, csrfToken: string): Promise<OrderOut> {
  return apiRequest<OrderOut>(`/api/v1/orders/${orderId}/pay`, {
    method: 'POST',
    csrfToken,
  })
}

export function fetchOrder(orderId: string): Promise<OrderOut> {
  return apiRequest<OrderOut>(`/api/v1/orders/${orderId}`)
}

export async function fetchOrders(
  status?: string,
): Promise<{ items: OrderOut[]; total: number }> {
  const query = new URLSearchParams({ limit: '20' })
  if (status) query.set('status', status)
  const result = await apiRequestWithMeta<OrderOut[], PageMeta>(`/api/v1/orders?${query}`)
  return { items: result.data, total: result.meta?.total ?? result.data.length }
}