import type {
  ArchiveComment,
  ArchiveData,
  ArchiveFilter,
  ArchivePost,
  ArchiveSource,
} from '../types'

const SOURCES: ArchiveSource[] = ['msglist', 'feeds', 'both']

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function asComment(value: unknown): ArchiveComment | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  const text = asString(record.text)
  if (!text) return null
  return {
    author: asString(record.author, '匿名'),
    text,
    createdAt: typeof record.createdAt === 'string' ? record.createdAt : null,
  }
}

function asSource(value: unknown): ArchiveSource {
  return SOURCES.includes(value as ArchiveSource) ? (value as ArchiveSource) : 'msglist'
}

function asPost(value: unknown): ArchivePost | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Record<string, unknown>
  const text = asString(record.text)
  const createdAt = asString(record.createdAt)
  const tid = asString(record.tid) || asString(record.id)

  if (!tid && !text) return null

  const images = Array.isArray(record.images)
    ? record.images.filter((item): item is string => typeof item === 'string' && item !== '')
    : []
  const comments = Array.isArray(record.comments)
    ? record.comments
        .map(asComment)
        .filter((item): item is ArchiveComment => item !== null)
    : []

  return {
    id: asString(record.id) || tid,
    tid,
    createdAt,
    text,
    images,
    comments,
    likes: asNumber(record.likes),
    deleted: record.deleted === true,
    source: asSource(record.source),
    repost: typeof record.repost === 'string' && record.repost ? record.repost : null,
  }
}

/**
 * 把外部 JSON 收敛成站点内部结构：字段缺失、类型不对、脏数据都不会让页面崩掉。
 * 时间无效但文字存在的记录会被保留，只是排到时间线的最后。
 */
export function normalizeArchive(raw: unknown): ArchiveData {
  const record = (raw ?? {}) as Record<string, unknown>
  const rawPosts = Array.isArray(record.posts) ? record.posts : []
  const posts = rawPosts
    .map(asPost)
    .filter((item): item is ArchivePost => item !== null)
    .sort(comparePosts)

  return {
    generatedAt: asString(record.generatedAt),
    uin: typeof record.uin === 'string' ? record.uin : undefined,
    posts,
  }
}

function timeValue(post: ArchivePost): number {
  const time = new Date(post.createdAt).getTime()
  return Number.isNaN(time) ? Number.NEGATIVE_INFINITY : time
}

/** 时间倒序；时间相同时按 tid 稳定排序，保证分页/刷新后顺序不变 */
export function comparePosts(a: ArchivePost, b: ArchivePost): number {
  const diff = timeValue(b) - timeValue(a)
  if (diff !== 0) return diff
  return a.tid.localeCompare(b.tid)
}

export function isDeleted(post: ArchivePost): boolean {
  return post.deleted
}

export function hasImages(post: ArchivePost): boolean {
  return post.images.length > 0
}

export function matchKeyword(post: ArchivePost, keyword: string): boolean {
  const needle = keyword.trim().toLowerCase()
  if (!needle) return true
  const haystack = [
    post.text,
    post.repost ?? '',
    ...post.comments.map((comment) => `${comment.author} ${comment.text}`),
  ]
    .join('\n')
    .toLowerCase()
  return haystack.includes(needle)
}

export function filterPosts(
  posts: ArchivePost[],
  filter: ArchiveFilter,
  keyword = '',
): ArchivePost[] {
  return posts.filter((post) => {
    if (filter === 'deleted' && !isDeleted(post)) return false
    if (filter === 'withImages' && !hasImages(post)) return false
    return matchKeyword(post, keyword)
  })
}

export type ArchiveStats = {
  total: number
  deleted: number
  images: number
  firstAt: string | null
  lastAt: string | null
}

export function computeStats(posts: ArchivePost[]): ArchiveStats {
  let deleted = 0
  let images = 0
  let first = Number.POSITIVE_INFINITY
  let last = Number.NEGATIVE_INFINITY

  for (const post of posts) {
    if (post.deleted) deleted += 1
    images += post.images.length
    const time = timeValue(post)
    if (Number.isFinite(time)) {
      if (time < first) first = time
      if (time > last) last = time
    }
  }

  return {
    total: posts.length,
    deleted,
    images,
    firstAt: Number.isFinite(first) ? new Date(first).toISOString() : null,
    lastAt: Number.isFinite(last) ? new Date(last).toISOString() : null,
  }
}

export type MonthGroup = { month: number; posts: ArchivePost[] }
export type YearGroup = { year: string; months: MonthGroup[] }

/** 按 年 → 月 分组，组内维持传入顺序（已是时间倒序） */
export function groupByYear(posts: ArchivePost[]): YearGroup[] {
  const groups: YearGroup[] = []
  const years = new Map<string, YearGroup>()
  const months = new Map<string, MonthGroup>()

  for (const post of posts) {
    const date = new Date(post.createdAt)
    const valid = !Number.isNaN(date.getTime())
    const year = valid ? String(date.getFullYear()) : '时间未知'
    const month = valid ? date.getMonth() + 1 : 0

    let yearGroup = years.get(year)
    if (!yearGroup) {
      yearGroup = { year, months: [] }
      years.set(year, yearGroup)
      groups.push(yearGroup)
    }

    const key = `${year}-${month}`
    let monthGroup = months.get(key)
    if (!monthGroup) {
      monthGroup = { month, posts: [] }
      months.set(key, monthGroup)
      yearGroup.months.push(monthGroup)
    }

    monthGroup.posts.push(post)
  }

  return groups
}

/** 图片既可能是本地相对路径，也可能是没下载成功的原始链接 */
export function resolveImageUrl(path: string, baseUrl: string): string {
  if (/^(https?:)?\/\//i.test(path) || path.startsWith('data:')) return path
  const base = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`
  return `${base}${path.replace(/^\.?\//, '')}`
}

