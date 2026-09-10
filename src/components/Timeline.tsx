import { groupByYear } from '../lib/archive'
import type { ArchivePost } from '../types'
import PostCard from './PostCard'

type Props = {
  posts: ArchivePost[]
  onOpenImage: (images: string[], index: number) => void
}

export default function Timeline({ posts, onOpenImage }: Props) {
  const groups = groupByYear(posts)

  return (
    <div className="space-y-10">
      {groups.map((group) => (
        <section key={group.year}>
          <h2 className="sticky top-14 z-10 -mx-2 mb-4 rounded-lg bg-ink-950/85 px-2 py-1 text-2xl font-semibold text-ember-400 backdrop-blur">
            {group.year}
          </h2>

          <div className="space-y-6">
            {group.months.map((month) => (
              <div key={`${group.year}-${month.month}`} className="relative pl-5 sm:pl-6">
                <span className="absolute left-0 top-2 h-px w-3 bg-ink-600 sm:w-4" />
                <span className="absolute left-0 top-0 h-full w-px bg-ink-800" />

                <h3 className="mb-3 text-sm font-medium tracking-wide text-slate-400">
                  {month.month === 0 ? '时间未知' : `${month.month} 月`}
                  <span className="ml-2 text-xs text-slate-600">{month.posts.length} 条</span>
                </h3>

                <div className="space-y-4">
                  {month.posts.map((post) => (
                    <PostCard key={post.id} post={post} onOpenImage={onOpenImage} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

