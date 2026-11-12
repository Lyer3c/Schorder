/**
 * 统一请求层。
 *
 * 约束（与后端契约一致）：
 * - 始终带 Cookie（credentials: 'include'）
 * - 非 GET 请求由调用方传 csrfToken，注入 X-CSRF-Token
 * - 后端统一返回 { ok, data, meta? } / { ok, error }，这里把 error 转成 ApiError
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

export interface Envelope<T> {
  ok: boolean
  data?: T
  meta?: unknown
  error?: ApiErrorPayload
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  csrfToken?: string | null
}

export interface MetaResult<T, M> {
  data: T
  meta: M
}

/** 发请求并返回完整信封（需要读 meta 时用，比如分页游标）。 */
export async function apiEnvelope<T>(path: string, options: RequestOptions = {}): Promise<Envelope<T>> {
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

  return payload ?? { ok: true }
}

/** 最常见用法：只要 data。 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const envelope = await apiEnvelope<T>(path, options)
  if (envelope.data === undefined) {
    throw new ApiError(200, { code: 'EMPTY_RESPONSE', message: '响应体为空' })
  }

  // 开发期护栏：泛型误传成 *Envelope 类型时，调用方会多拆一层导致 undefined。
  // 这类错误类型系统看不出来（泛型不做校验），所以这里主动拦一次。
  if (import.meta.env.DEV && looksLikeEnvelope(envelope.data)) {
    throw new Error(
      `apiRequest 已经拆过一层信封了：${path} 的泛型应填 data 的类型（如 MetaOut），而不是 MetaEnvelope`,
    )
  }

  return envelope.data
}

function looksLikeEnvelope(value: unknown): boolean {
  return (
    typeof value === 'object' &&
    value !== null &&
    'ok' in value &&
    'data' in value &&
    !('id' in value)
  )
}

/** 需要 data + meta 的用法（分页）。 */
export async function apiRequestWithMeta<T, M>(
  path: string,
  options: RequestOptions = {},
): Promise<MetaResult<T, M>> {
  const envelope = await apiEnvelope<T>(path, options)
  if (envelope.data === undefined) {
    throw new ApiError(200, { code: 'EMPTY_RESPONSE', message: '响应体为空' })
  }
  return { data: envelope.data, meta: envelope.meta as M }
}