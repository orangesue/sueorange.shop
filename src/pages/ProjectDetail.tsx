import { Link, Navigate, useParams } from 'react-router-dom'
import { findProject } from '../content/profile'

function Block({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium text-slate-100">{title}</h2>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex gap-2 text-sm leading-relaxed text-slate-300">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ember-500/70" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default function ProjectDetail() {
  const { slug } = useParams<{ slug: string }>()
  const project = slug ? findProject(slug) : undefined

  if (!project) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="space-y-8">
      <Link to="/" className="inline-block text-sm text-slate-400 transition-colors hover:text-ember-400">
        ← 返回首页
      </Link>

      <header className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h1 className="text-2xl font-semibold text-slate-50 sm:text-3xl">{project.name}</h1>
          <span className="text-xs text-slate-500">{project.period}</span>
        </div>
        <p className="text-sm text-slate-400">{project.subtitle}</p>
        <p className="text-sm text-ember-400/90">{project.role}</p>

        <div className="flex flex-wrap gap-2 pt-1">
          {project.tags.map((tag) => (
            <span key={tag} className="chip">
              {tag}
            </span>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-3 pt-2">
          {project.metrics.map((metric) => (
            <div key={metric.label} className="card px-3 py-2">
              <div className="text-sm font-semibold text-slate-100">{metric.value}</div>
              <div className="mt-0.5 text-[11px] text-slate-500">{metric.label}</div>
            </div>
          ))}
        </div>

        {project.links.length > 0 ? (
          <div className="flex flex-wrap gap-2 pt-1">
            {project.links.map((link) =>
              link.href.startsWith('http') ? (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="chip transition-colors hover:border-ember-500/50 hover:text-ember-400 focus-ring"
                >
                  {link.label} ↗
                </a>
              ) : (
                <Link
                  key={link.href}
                  to={link.href}
                  className="chip border-ember-500/40 text-ember-400 transition-colors hover:border-ember-500 focus-ring"
                >
                  {link.label}
                  {link.note ? <span className="ml-1 text-slate-500">· {link.note}</span> : null} →
                </Link>
              ),
            )}
          </div>
        ) : null}
      </header>

      <section className="card p-5">
        <h2 className="text-lg font-medium text-slate-100">项目背景</h2>
        <p className="mt-3 leading-relaxed text-slate-300">{project.detail.background}</p>
      </section>

      <Block title="我做了什么" items={project.detail.contributions} />
      <Block title="技术要点" items={project.detail.tech} />
      <Block title="结果" items={project.detail.outcomes} />

      {project.todo ? (
        <p className="rounded-xl border border-ember-500/30 bg-ember-500/10 px-4 py-3 text-sm text-ember-400">
          {project.todo}
        </p>
      ) : null}

      <Link to="/" className="inline-block text-sm text-slate-400 transition-colors hover:text-ember-400">
        ← 返回首页
      </Link>
    </div>
  )
}
