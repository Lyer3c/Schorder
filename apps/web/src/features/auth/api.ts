import type { components } from '@schorder/contract'

import { apiRequest } from '@/shared/api/client'

export type SessionUser = components['schemas']['UserOut']
export type SessionData = components['schemas']['SessionDataOut']

export function fetchSession(): Promise<SessionData> {
  return apiRequest<SessionData>('/api/v1/auth/session')
}

export function login(phone: string, password: string): Promise<SessionData> {
  return apiRequest<SessionData>('/api/v1/auth/login', {
    method: 'POST',
    body: { phone, password },
  })
}

export function register(
  phone: string,
  password: string,
  nickname: string,
): Promise<SessionData> {
  return apiRequest<SessionData>('/api/v1/auth/register', {
    method: 'POST',
    body: { phone, password, nickname },
  })
}

export function logout(csrfToken: string): Promise<unknown> {
  return apiRequest<unknown>('/api/v1/auth/logout', { method: 'POST', csrfToken })
}