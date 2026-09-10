const DATE_TIME = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const DATE_ONLY = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

function parse(value: string | Date | null | undefined): Date | null {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const date = parse(value)
  return date ? DATE_TIME.format(date) : '时间未知'
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = parse(value)
  return date ? DATE_ONLY.format(date) : '时间未知'
}

export function yearOf(value: string | Date | null | undefined): string {
  const date = parse(value)
  return date ? String(date.getFullYear()) : '时间未知'
}

export function monthLabel(month: number): string {
  return `${month} 月`
}

export function formatRange(
  from: string | Date | null | undefined,
  to: string | Date | null | undefined,
): string {
  const start = parse(from)
  const end = parse(to)
  if (!start || !end) return '—'
  return `${DATE_ONLY.format(start)} ~ ${DATE_ONLY.format(end)}`
}

