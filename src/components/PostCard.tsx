import { useState } from 'react'
import { resolveImageUrl } from '../lib/archive'
import { formatDateTime } from '../lib/format'
import type { ArchivePost } from '../types'

type Props = {
  post: ArchivePost
  onOpenImage: (images: string[], index: number) => void
}

const SOURCE_LABEL: Record<ArchivePost['source'], string> = {
  msglist: '现存说说',
  feeds: '互动记录',
  both: '两条通道',
}

function imageGridClass(count: number): string {
  if (count === 1) return 'grid-cols-1'
  if (count === 2 || count === 4) return 'grid-cols-2'
  return 'grid-cols-2 sm:grid-cols-3'
}

export default function PostCard({ post, onOpenImage }: Props) {
  const [showComments, setShowComments] = useState(false)
  const base = import.meta.env.BASE_URL
  const images = post.images.map((path) => resolveImageUrl(path, base))
  const hasComments = post.comments.length > 0

  return (
    <article className="card p-4 sm:p-5">
      <header className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <time dateTime={post.createdAt || undefined}>{formatDateTime(post.createdAt)}</time>
        {post.deleted ? (
          <span className="chip border-ember-500/40 bg-ember-500/10 text-ember-400">已找回</span>
        ) : null}
        <span className="chip">{SOURCE_LABEL[post.source]}</span>
        {post.likes > 0 ? <span className="chip">{post.likes} 赞</span> : null}
      </header>

      {post.text ? (
        <p className="mt-3 whitespace-pre-wrap break-words leading-relaxed text-slate-200">
          {post.text}
        </p>
      ) : (
        <p className="mt-3 text-sm italic text-slate-500">（这条记录没有正文，只剩互动痕迹）</p>
      )}

      {post.repost ? (
        <blockquote className="mt-3 rounded-xl border-l-2 border-ember-500/50 bg-ink-800/60 px-3 py-2 text-sm whitespace-pre-wrap break-words text-slate-400">
          {post.repost}
        </blockquote>
      ) : null}

      {images.length > 0 ? (
        <div className={`mt-4 grid gap-2 ${imageGridClass(images.length)}`}>
          {images.map((url, index) => (
            <button
              key={`${post.id}-${url}`}
              type="button"
              onClick={() => onOpenImage(images, index)}
              className="group relative overflow-hidden rounded-xl border border-ink-700 focus-ring"
              aria-label={`查看第 ${index + 1} 张图片`}
            >
              <img
                src={url}
                alt=""
                loading="lazy"
                // 腾讯图床会拦非 qq.com 的 Referer：不带 Referer 才给真图
                referrerPolicy="no-referrer"
                className="h-40 w-full object-cover transition-transform duration-300 group-hover:scale-[1.03] sm:h-48"
              />
            </button>
          ))}
        </div>
      ) : null}

      {hasComments ? (
        <div className="mt-4 border-t border-ink-800 pt-3">
          <button
            type="button"
            onClick={() => setShowComments((value) => !value)}
            aria-expanded={showComments}
            className="text-xs text-slate-400 transition-colors hover:text-ember-400 focus-ring rounded"
          >
            {showComments ? '收起评论' : `展开 ${post.comments.length} 条评论`}
          </button>

          {showComments ? (
            <ul className="mt-3 space-y-2">
              {post.comments.map((comment, index) => (
                <li
                  key={`${post.id}-comment-${index}`}
                  className="rounded-lg bg-ink-800/60 px-3 py-2 text-sm"
                >
                  <span className="text-ember-400">{comment.author || '匿名'}</span>
                  <span className="mx-2 text-slate-600">·</span>
                  <span className="text-slate-500">
                    {comment.createdAt ? formatDateTime(comment.createdAt) : '时间未知'}
                  </span>
                  <p className="mt-1 whitespace-pre-wrap break-words text-slate-300">
                    {comment.text}
                  </p>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}
