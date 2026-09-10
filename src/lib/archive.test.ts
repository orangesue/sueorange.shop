import { describe, expect, it } from 'vitest'
import {
  comparePosts,
  computeStats,
  filterPosts,
  groupByYear,
  matchKeyword,
  normalizeArchive,
  resolveImageUrl,
} from './archive'
import type { ArchivePost } from '../types'

function makePost(overrides: Partial<ArchivePost> = {}): ArchivePost {
  return {
    id: '1',
    tid: '1',
    createdAt: '2020-05-01T10:00:00.000Z',
    text: '正文',
    images: [],
    comments: [],
    likes: 0,
    deleted: false,
    source: 'msglist',
    repost: null,
    ...overrides,
  }
}

describe('normalizeArchive', () => {
  it('容忍缺失字段并丢弃完全空白的记录', () => {
    const data = normalizeArchive({
      generatedAt: '2026-09-10T00:00:00.000Z',
      posts: [
        { tid: 'a', text: '留下这条' },
        null,
        { images: ['x.jpg'] },
        { tid: 'b', text: '也留下', likes: '12', deleted: true, source: 'feeds' },
      ],
    })

    expect(data.posts).toHaveLength(2)
    expect(data.posts.map((post) => post.tid).sort()).toEqual(['a', 'b'])
    expect(data.posts[1].likes).toBe(12)
    expect(data.posts[1].deleted).toBe(true)
    expect(data.posts[1].source).toBe('feeds')
  })

  it('非法 source 回退成 msglist，非法图片项被剔除', () => {
    const data = normalizeArchive({
      posts: [{ tid: 'c', text: 'x', source: 'weird', images: ['ok.jpg', 3, ''] }],
    })
    expect(data.posts[0].source).toBe('msglist')
    expect(data.posts[0].images).toEqual(['ok.jpg'])
  })

  it('comment 缺少正文时被丢弃', () => {
    const data = normalizeArchive({
      posts: [
        {
          tid: 'd',
          text: 'x',
          comments: [{ author: '甲', text: '在' }, { author: '乙' }],
        },
      ],
    })
    expect(data.posts[0].comments).toHaveLength(1)
    expect(data.posts[0].comments[0].author).toBe('甲')
  })

  it('按时间倒序排列，无时间记录排到最后', () => {
    const data = normalizeArchive({
      posts: [
        { tid: 'old', text: 'x', createdAt: '2015-01-01T00:00:00.000Z' },
        { tid: 'new', text: 'x', createdAt: '2021-01-01T00:00:00.000Z' },
        { tid: 'none', text: 'x', createdAt: '' },
      ],
    })
    expect(data.posts.map((post) => post.tid)).toEqual(['new', 'old', 'none'])
  })
})

describe('search / filter', () => {
  const posts = [
    makePost({ tid: '1', text: '今天吃了橘子', createdAt: '2021-03-01T00:00:00.000Z' }),
    makePost({
      tid: '2',
      text: '被删掉的一条',
      deleted: true,
      images: ['data/images/2/1.jpg'],
      createdAt: '2022-03-01T00:00:00.000Z',
    }),
    makePost({
      tid: '3',
      text: '有评论的',
      comments: [{ author: '小明', text: '橘子好吃' }],
      createdAt: '2020-03-01T00:00:00.000Z',
    }),
  ]

  it('关键词能命中正文', () => {
    expect(filterPosts(posts, 'all', '橘子').map((post) => post.tid)).toEqual(['1', '3'])
  })

  it('关键词能命中评论', () => {
    expect(filterPosts(posts, 'all', '小明').map((post) => post.tid)).toEqual(['3'])
  })

  it('仅已删除筛选', () => {
    expect(filterPosts(posts, 'deleted').map((post) => post.tid)).toEqual(['2'])
  })

  it('仅有图筛选', () => {
    expect(filterPosts(posts, 'withImages').map((post) => post.tid)).toEqual(['2'])
  })

  it('空关键词与空白关键词都不过滤', () => {
    expect(matchKeyword(posts[0], '   ')).toBe(true)
    expect(filterPosts(posts, 'all', '')).toHaveLength(3)
  })
})

describe('stats / grouping', () => {
  const posts = [
    makePost({ tid: '1', createdAt: '2021-03-01T00:00:00.000Z', images: ['a.jpg'] }),
    makePost({ tid: '2', createdAt: '2021-04-05T00:00:00.000Z', deleted: true }),
    makePost({ tid: '3', createdAt: '2022-04-05T00:00:00.000Z' }),
  ]

  it('统计总数、已删除数、图片数与时间跨度', () => {
    const stats = computeStats(posts)
    expect(stats.total).toBe(3)
    expect(stats.deleted).toBe(1)
    expect(stats.images).toBe(1)
    expect(stats.firstAt).toBe('2021-03-01T00:00:00.000Z')
    expect(stats.lastAt).toBe('2022-04-05T00:00:00.000Z')
  })

  it('按年分组时月份不重复出现', () => {
    // 真实数据在 normalizeArchive 里已经按时间倒序，这里保持一致
    const grouped = groupByYear([...posts].sort(comparePosts))
    expect(grouped.map((group) => group.year)).toEqual(['2022', '2021'])
    const year2021 = grouped.find((group) => group.year === '2021')
    expect(year2021?.months.map((month) => month.month)).toEqual([4, 3])
    expect(year2021?.months[0].posts.map((post) => post.tid)).toEqual(['2'])
  })

  it('时间无效的记录归入「时间未知」组', () => {
    const grouped = groupByYear([makePost({ tid: 'x', createdAt: '' })])
    expect(grouped[0].year).toBe('时间未知')
    expect(grouped[0].months[0].month).toBe(0)
  })
})

describe('sorting / image url', () => {
  it('时间相同的记录按 tid 稳定排序', () => {
    const a = makePost({ tid: 'a' })
    const b = makePost({ tid: 'b' })
    expect([b, a].sort(comparePosts).map((post) => post.tid)).toEqual(['a', 'b'])
  })

  it('本地图片拼上 base，远程地址原样返回', () => {
    expect(resolveImageUrl('data/images/1/1.jpg', '/sueorange.shop/')).toBe(
      '/sueorange.shop/data/images/1/1.jpg',
    )
    expect(resolveImageUrl('data/images/1/1.jpg', '/')).toBe('/data/images/1/1.jpg')
    expect(resolveImageUrl('https://example.com/a.jpg', '/')).toBe('https://example.com/a.jpg')
  })
})
