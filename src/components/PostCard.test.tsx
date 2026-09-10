import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PostCard from './PostCard'
import type { ArchivePost } from '../types'

function makePost(overrides: Partial<ArchivePost> = {}): ArchivePost {
  return {
    id: '1',
    tid: '1',
    createdAt: '2021-03-01T02:00:00.000Z',
    text: '今天天气不错',
    images: [],
    comments: [],
    likes: 0,
    deleted: false,
    source: 'msglist',
    repost: null,
    ...overrides,
  }
}

describe('PostCard', () => {
  it('已删除的说说显示「已找回」标记', () => {
    render(
      <PostCard
        post={makePost({ deleted: true, source: 'feeds' })}
        onOpenImage={vi.fn()}
      />,
    )

    expect(screen.getByText('已找回')).toBeInTheDocument()
    expect(screen.getByText('互动记录')).toBeInTheDocument()
  })

  it('现存说说不显示「已找回」标记', () => {
    render(<PostCard post={makePost()} onOpenImage={vi.fn()} />)

    expect(screen.queryByText('已找回')).not.toBeInTheDocument()
    expect(screen.getByText('今天天气不错')).toBeInTheDocument()
  })

  it('没有正文但残留互动痕迹时给出提示', () => {
    render(<PostCard post={makePost({ text: '', deleted: true })} onOpenImage={vi.fn()} />)

    expect(screen.getByText(/没有正文/)).toBeInTheDocument()
  })

  it('评论数量会展示出来', () => {
    render(
      <PostCard
        post={makePost({ comments: [{ author: '小明', text: '沙发' }] })}
        onOpenImage={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: '展开 1 条评论' })).toBeInTheDocument()
  })
})

