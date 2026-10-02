const commonCodes = ['CNY', 'USD', 'EUR', 'JPY', 'GBP', 'HKD', 'SGD', 'AUD', 'CAD', 'CHF']
const displayNames = typeof Intl.DisplayNames === 'function'
  ? new Intl.DisplayNames(['zh-CN'], { type: 'currency' }) : undefined

export function currencyName(code: string, fallback: string) {
  try {
    const localized = displayNames?.of(code)
    return localized && localized !== code ? localized : fallback
  } catch { return fallback }
}

export function sortCurrencies<T extends { code: string }>(items: T[]) {
  return [...items].sort((a, b) => {
    const ai = commonCodes.indexOf(a.code), bi = commonCodes.indexOf(b.code)
    return (ai < 0 ? 100 : ai) - (bi < 0 ? 100 : bi) || a.code.localeCompare(b.code)
  })
}
