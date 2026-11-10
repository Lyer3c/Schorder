import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="mx-auto max-w-md rounded-card border border-ink-300/60 bg-surface p-8 text-center">
      <p className="text-4xl font-semibold text-brand-500">404</p>
      <h1 className="mt-3 text-lg font-semibold">没有这个页面</h1>
      <p className="mt-2 text-sm text-ink-500">链接可能已失效，或者它还在开发中。</p>
      <Link
        to="/"
        className="mt-6 inline-flex rounded-pill bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
      >
        回到首页
      </Link>
    </section>
  )
}