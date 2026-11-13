import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface CartLine {
  key: string
  dishId: string
  name: string
  unitPriceCents: number
  quantity: number
  optionIds: string[]
  optionNames: string[]
}

interface CartState {
  stallId: string | null
  stallName: string | null
  minOrderCents: number
  lines: CartLine[]
  add: (line: Omit<CartLine, 'key' | 'quantity'>, stall: { id: string; name: string; minOrderCents: number }) => void
  increase: (key: string) => void
  decrease: (key: string) => void
  remove: (key: string) => void
  clear: () => void
}

function lineKey(dishId: string, optionIds: string[]): string {
  return `${dishId}:${[...optionIds].sort().join(',')}`
}

export const useCart = create<CartState>()(
  persist(
    (set) => ({
      stallId: null,
      stallName: null,
      minOrderCents: 0,
      lines: [],

      add: (line, stall) =>
        set((state) => {
          // 换一家店就清空：一个订单只能来自一个档口
          const lines =
            state.stallId && state.stallId !== stall.id ? [] : state.lines
          const key = lineKey(line.dishId, line.optionIds)
          const existing = lines.find((item) => item.key === key)
          const next = existing
            ? lines.map((item) =>
                item.key === key ? { ...item, quantity: item.quantity + 1 } : item,
              )
            : [...lines, { ...line, key, quantity: 1 }]
          return {
            stallId: stall.id,
            stallName: stall.name,
            minOrderCents: stall.minOrderCents,
            lines: next,
          }
        }),

      increase: (key) =>
        set((state) => ({
          lines: state.lines.map((item) =>
            item.key === key ? { ...item, quantity: item.quantity + 1 } : item,
          ),
        })),

      decrease: (key) =>
        set((state) => ({
          lines: state.lines
            .map((item) =>
              item.key === key ? { ...item, quantity: item.quantity - 1 } : item,
            )
            .filter((item) => item.quantity > 0),
        })),

      remove: (key) =>
        set((state) => ({ lines: state.lines.filter((item) => item.key !== key) })),

      clear: () => set({ stallId: null, stallName: null, minOrderCents: 0, lines: [] }),
    }),
    { name: 'schorder-cart' },
  ),
)

export function cartTotal(lines: CartLine[]): number {
  return lines.reduce((sum, line) => sum + line.unitPriceCents * line.quantity, 0)
}

export function cartCount(lines: CartLine[]): number {
  return lines.reduce((sum, line) => sum + line.quantity, 0)
}