import { isRouteErrorResponse, Link, useRouteError } from 'react-router-dom'

/**
 * 路由级错误兜底。
 *
 * 没有它，渲染期报错会直接炸出 React Router 的默认错误页
 * （左上角一行 "Unexpected Application Error!"），对用户毫无信息量。
 */
export function RouteErrorPage() {
  const error = useRouteError()

  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : '未知错误'

  return (
    <section className="mx-auto max-w-md rounded-card border border-ink-300/60 bg-surface p-8 text-center">
      <p className="text-3xl font-semibold text-brand-500">哎呀</p>
      <h1 className="mt-3 text-lg font-semibold">页面出错了</h1>
      <p className="mt-2 break-words text-sm text-ink-500">{message}</p>
      <p className="mt-2 text-xs text-ink-500">可以刷新重试，或回首页重新进入。</p>
      <div className="mt-6 flex justify-center gap-3">
        <button
          type="button"
          className="rounded-pill border border-ink-300 px-4 py-2 text-sm hover:bg-canvas"
          onClick={() => window.location.reload()}
        >
          刷新
        </button>
        <Link
          to="/"
          className="rounded-pill bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          回到首页
        </Link>
      </div>
    </section>
  )
}