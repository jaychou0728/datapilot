export function formatNumber(n: number | string): string {
  if (typeof n === 'string') n = parseFloat(n)
  if (isNaN(n)) return String(n)
  return n.toLocaleString('zh-CN')
}

export function formatDate(d: string): string {
  if (!d) return ''
  const date = new Date(d)
  if (isNaN(date.getTime())) return d
  return date.toLocaleDateString('zh-CN')
}

export function truncateText(text: string, max: number = 50): string {
  if (!text) return ''
  if (text.length <= max) return text
  return text.slice(0, max) + '...'
}
