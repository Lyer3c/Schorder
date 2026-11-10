/**
 * 统一请求层。
 *
 * 约束（与后端契约一致）：
 * - 始终带 Cookie（credentials: 'include'）
 * - 非 GET 请求由调用方传 csrfToken，注入 X-CSRF-Token
 * - 后端统一返回 { ok, data } / { ok, error }，这里只把 error 转成 ApiError
 */

export interface ApiErrorPayload {
  code: string
  message: string
  details?: Record<string, unknown>
  traceId?: string | null
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly traceId: string | null

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message)
    this.name = 'ApiError'
    this.status = status
    this.code = payload.code
    this.traceId = payload.traceId ?? null
  }
}

interface Envelope<T> {
  ok: boolean
  data?: T
  error?: ApiErrorPayload
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  csrfToken?: string | null
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, csrfToken, headers, ...rest } = options

  const requestHeaders = new Headers(headers)
  requestHeaders.set('Accept', 'application/json')
  if (body !== undefined) {
    requestHeaders.set('Content-Type', 'application/json')
  }
  if (csrfToken) {
    requestHeaders.set('X-CSRF-Token', csrfToken)
  }

  const init: RequestInit = {
    ...rest,
    headers: requestHeaders,
    credentials: 'include',
  }
  if (body !== undefined) {
    init.body = JSON.stringify(body)
  }

  const response = await fetch(path, init)

  const contentType = response.headers.get('content-type') ?? ''
  const payload: Envelope<T> | null = contentType.includes('application/json')
    ? ((await response.json()) as Envelope<T>)
    : null

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.error ?? {
        code: 'HTTP_ERROR',
        message: response.statusText || '请求失败',
        traceId: response.headers.get('X-Request-Id'),
      },
    )
  }

  if (payload === null || payload.data === undefined) {
    throw new ApiError(response.status, {
      code: 'EMPTY_RESPONSE',
      message: '响应体为空',
      traceId: response.headers.get('X-Request-Id'),
    })
  }

  return payload.data
}