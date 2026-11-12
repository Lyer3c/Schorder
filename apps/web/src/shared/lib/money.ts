/** 金额统一以「分」传输，只在展示层转成元。 */

export function yuan(cents: number): string {
  const value = cents / 100
  return Number.isInteger(value) ? `${value}` : value.toFixed(2)
}

export function yuanWithSymbol(cents: number): string {
  return `¥${yuan(cents)}`
}