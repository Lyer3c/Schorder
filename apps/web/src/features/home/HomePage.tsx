import { useQuery } from '@tanstack/react-query'

import { apiRequest } from '@/shared/api/client'
import { queryKeys } from '@/shared/api/queryKeys'
import type { MetaEnvelope } from '@/features/home/api'

export function HomePage() {
  const meta = useQuery({
    queryKey: queryKeys.meta,
    queryFn: () => apiRequest<MetaEnvelope>('/api/v1/meta'),
  })

  return (
    <section className="space-y-6">
      <div className="rounded-card bg-surface p-6 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight">今天想吃点什么？</h1>
        <p className="mt-2 text-sm leading-6 text-ink-500">
          M0 骨架已就绪：前端路由、后端 API、契约生成三条链路都通了。M1 开始接入档口与菜品。
        </p>
      </div>

      <div className="rounded-card border border-ink-300/60 bg-surface p-5">
        <h2 className="text-sm font-medium text-ink-700">后端连通性</h2>

        {meta.isPending ? (
          <p className="mt-3 text-sm text-ink-500">检测中…</p>
        ) : null}

        {meta.isError ? (
          <p className="mt-3 text-sm text-red-600">
            连接失败：{meta.error instanceof Error ? meta.error.message : '未知错误'}
          </p>
        ) : null}

        {meta.data ? (
          <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-ink-500">服务</dt>
              <dd className="mt-1 font-medium">{meta.data.data.name}</dd>
            </div>
            <div>
              <dt className="text-ink-500">版本 / 环境</dt>
              <dd className="mt-1 font-medium">
                v{meta.data.data.version} · {meta.data.data.env}
              </dd>
            </div>
            <div>
              <dt className="text-ink-500">服务器时间</dt>
              <dd className="mt-1 font-medium">
                {new Date(meta.data.data.serverTime).toLocaleString('zh-CN')}
              </dd>
            </div>
          </dl>
        ) : null}
      </div>
    </section>
  )
}