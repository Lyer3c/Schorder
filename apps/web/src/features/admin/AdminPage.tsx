export function AdminPage() {
  return (
    <section className="rounded-card border border-dashed border-ink-300 bg-surface p-8 text-center">
      <h1 className="text-lg font-semibold">管理后台</h1>
      <p className="mt-2 text-sm text-ink-500">
        将在 M5 交付：档口审核、用户封禁、全局订单处置、经营看板。所有写操作要求填写理由并落审计。
      </p>
    </section>
  )
}