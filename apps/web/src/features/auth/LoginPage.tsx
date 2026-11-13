import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { login, register } from '@/features/auth/api'
import { useAuth } from '@/features/auth/store'
import { ApiError } from '@/shared/api/client'

export function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const setSession = useAuth((state) => state.setSession)
  const next = params.get('next') ?? '/'

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      const session =
        mode === 'login'
          ? await login(phone, password)
          : await register(phone, password, nickname)
      setSession(session)
      navigate(next, { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : '网络异常，请稍后重试')
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="mx-auto max-w-sm">
      <div className="rounded-card bg-surface p-6 shadow-sm">
        <div className="mb-5 flex gap-2 text-sm">
          {(['login', 'register'] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setMode(item)
                setError(null)
              }}
              className={[
                'rounded-pill px-3 py-1.5',
                mode === item ? 'bg-brand-500 text-white' : 'bg-canvas text-ink-700',
              ].join(' ')}
            >
              {item === 'login' ? '登录' : '注册'}
            </button>
          ))}
        </div>

        <form className="space-y-3" onSubmit={(event) => void submit(event)}>
          <Field label="手机号">
            <input
              className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm"
              value={phone}
              inputMode="numeric"
              autoComplete="username"
              onChange={(event) => setPhone(event.target.value)}
              placeholder="13800000001"
              required
            />
          </Field>

          {mode === 'register' ? (
            <Field label="昵称">
              <input
                className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm"
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                placeholder="张同学"
                required
              />
            </Field>
          ) : null}

          <Field label="密码">
            <input
              className="w-full rounded-md border border-ink-300 px-3 py-2 text-sm"
              type="password"
              value={password}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="至少 8 位，含字母和数字"
              required
            />
          </Field>

          {error ? <p className="text-xs text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-pill bg-brand-500 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-60"
          >
            {pending ? '处理中…' : mode === 'login' ? '登录' : '注册并登录'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-ink-500">
          演示账号：13800000001 / schorder123
        </p>
      </div>
    </section>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-ink-500">{label}</span>
      {children}
    </label>
  )
}