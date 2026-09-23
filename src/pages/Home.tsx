import { Link } from 'react-router-dom'
import Avatar from '../components/Avatar'
import { profile } from '../content/profile'
import type { LinkItem } from '../content/profile'

/** 站内链接走路由（子路径部署才不会跳错），站外链接新窗口打开 */
function SmartLink({ link, className }: { link: LinkItem; className: string }) {
  const isExternal = link.href.startsWith('http')
  const content = (
    <>
      {link.label}
      {link.note ? <span className="ml-1 text-slate-500">· {link.note}</span> : null}
      {isExternal ? ' ↗' : ' →'}
    </>
  )

  if (isExternal) {
    return (
      <a href={link.href} target="_blank" rel="noreferrer" className={className}>
        {content}
      </a>
    )
  }

  return (
    <Link to={link.href} className={className}>
      {content}
    </Link>
  )
}

function SectionTitle({ id, title, note }: { id?: string; title: string; note?: string }) {
  return (
    <div id={id} className="scroll-mt-20">
      <h2 className="text-xl font-semibold text-slate-100 sm:text-2xl">{title}</h2>
      {note ? <p className="mt-1 text-sm text-slate-500">{note}</p> : null}
    </div>
  )
}

export default function Home() {
  const jump = [
    { href: '#projects', label: '项目经历' },
    { href: '#experience', label: '实习经历' },
    { href: '#skills', label: '技能' },
    { href: '#contact', label: '联系我' },
  ]

  return (
    <div className="space-y-14">
      <section className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
        <Avatar src={profile.avatar} name={profile.name} />

        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-ember-400">{profile.handle}</p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            {profile.name}
            <span className="ml-3 text-base font-normal text-slate-500">{profile.enName}</span>
          </h1>
          <p className="text-sm text-slate-400">{profile.headline}</p>
          <p className="max-w-xl pt-1 text-slate-300">{profile.tagline}</p>
        </div>
      </section>

      <section className="space-y-3">
        {profile.intro.map((paragraph) => (
          <p key={paragraph} className="leading-relaxed text-slate-300">
            {paragraph}
          </p>
        ))}
      </section>

      <section className="flex flex-wrap gap-2">
        {profile.links.map((link) => (
          <SmartLink
            key={link.href}
            link={link}
            className="chip transition-colors hover:border-ember-500/50 hover:text-ember-400 focus-ring"
          />
        ))}
      </section>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {profile.highlights.map((item) => (
          <div key={item.label} className="card px-4 py-3">
            <div className="text-lg font-semibold text-ember-400">{item.value}</div>
            <div className="mt-1 text-xs text-slate-500">{item.label}</div>
          </div>
        ))}
      </section>

      <nav className="flex flex-wrap gap-2 text-sm">
        {jump.map((item) => (
          <a key={item.href} href={item.href} className="chip hover:border-ember-500/50 hover:text-ember-400">
            {item.label} ↓
          </a>
        ))}
      </nav>

      <section className="space-y-5">
        <SectionTitle
          id="projects"
          title="项目经历"
          note="两个从零做到能跑起来的项目，点进详情能看到具体做了什么。"
        />

        <div className="space-y-4">
          {profile.projects.map((project) => (
            <article key={project.slug} className="card p-5 transition-colors hover:border-ember-500/40">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-lg font-medium text-slate-100">{project.name}</h3>
                <span className="text-xs text-slate-500">{project.period}</span>
              </div>

              <p className="mt-1 text-sm text-ember-400/90">{project.role}</p>
              <p className="mt-3 leading-relaxed text-slate-300">{project.summary}</p>

              <div className="mt-4 flex flex-wrap gap-2">
                {project.tags.map((tag) => (
                  <span key={tag} className="chip">
                    {tag}
                  </span>
                ))}
              </div>

              <div className="mt-4 grid grid-cols-3 gap-3">
                {project.metrics.map((metric) => (
                  <div key={metric.label} className="rounded-xl bg-ink-800/60 px-3 py-2">
                    <div className="text-sm font-semibold text-slate-100">{metric.value}</div>
                    <div className="mt-0.5 text-[11px] text-slate-500">{metric.label}</div>
                  </div>
                ))}
              </div>

              <div className="mt-5 flex flex-wrap gap-3 text-sm">
                <Link
                  to={`/projects/${project.slug}`}
                  className="rounded-full bg-ember-500/15 px-4 py-1.5 text-ember-400 transition-colors hover:bg-ember-500/25 focus-ring"
                >
                  查看详情
                </Link>
                {project.links
                  .filter((link) => link.href.startsWith('http'))
                  .map((link) => (
                    <a
                      key={link.href}
                      href={link.href}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-full border border-ink-600 px-4 py-1.5 text-slate-300 transition-colors hover:border-ember-500/50 hover:text-ember-400 focus-ring"
                    >
                      {link.label} ↗
                    </a>
                  ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-5">
        <SectionTitle id="experience" title="实习与研学经历" />

        <div className="space-y-5">
          {profile.experiences.map((item) => (
            <article key={item.org} className="card p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-base font-medium text-slate-100">{item.org}</h3>
                <span className="text-xs text-slate-500">{item.period}</span>
              </div>
              <p className="mt-1 text-sm text-ember-400/90">{item.role}</p>
              <ul className="mt-3 space-y-2">
                {item.points.map((point) => (
                  <li key={point} className="flex gap-2 text-sm leading-relaxed text-slate-300">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ember-500/70" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-5">
        <SectionTitle id="skills" title="技能" />
        <div className="grid gap-3 sm:grid-cols-2">
          {profile.skills.map((group) => (
            <div key={group.group} className="card p-4">
              <div className="text-sm font-medium text-slate-200">{group.group}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {group.items.map((item) => (
                  <span key={item} className="chip">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-5">
        <SectionTitle title="校园经历" />
        <ul className="space-y-2">
          {profile.campus.map((item) => (
            <li key={item} className="flex gap-2 text-sm leading-relaxed text-slate-300">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ember-500/70" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>

      <section id="contact" className="scroll-mt-20">
        <div className="card p-5">
          <h2 className="text-xl font-semibold text-slate-100">联系我</h2>
          <p className="mt-2 text-sm text-slate-400">
            简历里的实习与项目都在这页上了。想聊技术、聊项目，或者需要更详细的版本，随时找我。
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {profile.links.map((link) => (
              <SmartLink
                key={link.href}
                link={link}
                className="chip transition-colors hover:border-ember-500/50 hover:text-ember-400 focus-ring"
              />
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
