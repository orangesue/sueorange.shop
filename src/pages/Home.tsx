import { Link } from 'react-router-dom'
import Avatar from '../components/Avatar'
import { useArchive } from '../hooks/useArchive'
import { computeStats } from '../lib/archive'
import { formatRange } from '../lib/format'
import { siteConfig } from '../site.config'

export default function Home() {
  const { data } = useArchive()
  const stats = data ? computeStats(data.posts) : null

  return (
    <div className="space-y-10">
      <section className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
        <Avatar src={siteConfig.avatar} name={siteConfig.name} />

        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-ember-400">
            {siteConfig.handle}
          </p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            {siteConfig.name}
          </h1>
          <p className="max-w-xl text-slate-400">{siteConfig.tagline}</p>
        </div>
      </section>

      <section className="space-y-3">
        {siteConfig.bio.map((paragraph) => (
          <p key={paragraph} className="leading-relaxed text-slate-300">
            {paragraph}
          </p>
        ))}
      </section>

      {siteConfig.links.length > 0 ? (
        <section className="flex flex-wrap gap-2">
          {siteConfig.links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              target="_blank"
              rel="noreferrer"
              className="chip transition-colors hover:border-ember-500/50 hover:text-ember-400 focus-ring"
            >
              {link.label} ↗
            </a>
          ))}
        </section>
      ) : null}

      <section>
        <Link
          to="/archive"
          className="card block p-5 transition-colors hover:border-ember-500/50 hover:bg-ink-800/70 focus-ring sm:p-6"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-medium text-slate-100">{siteConfig.archive.title}</h2>
              <p className="mt-1 max-w-lg text-sm leading-relaxed text-slate-400">
                {siteConfig.archive.intro}
              </p>
            </div>
            <span className="shrink-0 text-2xl text-ember-400">→</span>
          </div>

          {stats ? (
            <p className="mt-4 text-xs text-slate-500">
              已收录 {stats.total} 条 · 其中 {stats.deleted} 条是已删除后被找回 ·{' '}
              {formatRange(stats.firstAt, stats.lastAt)}
            </p>
          ) : null}
        </Link>
      </section>
    </div>
  )
}

