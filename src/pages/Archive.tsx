import { useMemo, useState } from 'react'
import FilterBar from '../components/FilterBar'
import Lightbox from '../components/Lightbox'
import StatsBar from '../components/StatsBar'
import Timeline from '../components/Timeline'
import { useArchive } from '../hooks/useArchive'
import { computeStats, filterPosts } from '../lib/archive'
import { formatDateTime } from '../lib/format'
import { siteConfig } from '../site.config'
import type { ArchiveFilter } from '../types'

type LightboxState = { images: string[]; index: number } | null

export default function Archive() {
  const { status, data, isDemo, error } = useArchive()
  const [filter, setFilter] = useState<ArchiveFilter>('all')
  const [keyword, setKeyword] = useState('')
  const [lightbox, setLightbox] = useState<LightboxState>(null)

  const posts = data?.posts ?? []
  const stats = useMemo(() => computeStats(posts), [posts])
  const visible = useMemo(
    () => filterPosts(posts, filter, keyword),
    [posts, filter, keyword],
  )

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-slate-50">{siteConfig.archive.title}</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-400">
          {siteConfig.archive.intro}
        </p>
        {data?.generatedAt ? (
          <p className="text-xs text-slate-600">
            导出时间：{formatDateTime(data.generatedAt)}
            {data.uin ? ` · UIN ${data.uin}` : ''}
          </p>
        ) : null}
      </header>

      {isDemo ? (
        <p className="rounded-xl border border-ember-500/30 bg-ember-500/10 px-4 py-3 text-sm text-ember-400">
          当前是演示数据。在本地跑一次
          <code className="mx-1 rounded bg-ink-950/60 px-1.5 py-0.5">tools/qzone/fetch.py</code>
          之后，这里会变成你自己的真实归档。
        </p>
      ) : null}

      {status === 'loading' ? (
        <p className="py-12 text-center text-sm text-slate-500">正在读取归档…</p>
      ) : null}

      {status === 'error' ? (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          归档文件读取失败：{error}
        </p>
      ) : null}

      {status === 'ready' ? (
        <>
          <StatsBar stats={stats} />
          <FilterBar
            filter={filter}
            keyword={keyword}
            onFilterChange={setFilter}
            onKeywordChange={setKeyword}
          />

          {visible.length === 0 ? (
            <p className="card px-4 py-12 text-center text-sm text-slate-500">
              没有符合条件的说说。试试换个关键词，或者切回「全部」。
            </p>
          ) : (
            <>
              <p className="text-xs text-slate-600">当前显示 {visible.length} 条</p>
              <Timeline
                posts={visible}
                onOpenImage={(images, index) => setLightbox({ images, index })}
              />
            </>
          )}
        </>
      ) : null}

      {lightbox ? (
        <Lightbox
          images={lightbox.images}
          index={lightbox.index}
          onClose={() => setLightbox(null)}
          onIndexChange={(index) =>
            setLightbox((current) => (current ? { ...current, index } : current))
          }
        />
      ) : null}
    </div>
  )
}

