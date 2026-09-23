import { NavLink, Outlet } from 'react-router-dom'
import { profile } from '../content/profile'

function navClass({ isActive }: { isActive: boolean }): string {
  return [
    'rounded-full px-3.5 py-1.5 text-sm transition-colors focus-ring',
    isActive
      ? 'bg-ember-500/15 text-ember-400'
      : 'text-slate-400 hover:text-slate-100 hover:bg-ink-800/70',
  ].join(' ')
}

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-ink-800/80 bg-ink-950/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 focus-ring rounded-full">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-ember-500/15 text-sm font-semibold text-ember-400">
              {profile.name.slice(0, 1)}
            </span>
            <span className="text-sm font-medium tracking-wide text-slate-200">
              {profile.name}
            </span>
          </NavLink>

          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navClass}>
              首页
            </NavLink>
            <NavLink to="/archive" className={navClass}>
              归档
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:py-12">
        <Outlet />
      </main>

      <footer className="border-t border-ink-800/80 py-6">
        <div className="mx-auto w-full max-w-4xl px-4 text-center text-xs text-slate-500">
          {profile.name} · {profile.enName} · {profile.footerNote}
        </div>
      </footer>
    </div>
  )
}
