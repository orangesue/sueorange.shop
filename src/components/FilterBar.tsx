import type { ArchiveFilter } from '../types'

const TABS: { key: ArchiveFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'deleted', label: '已找回' },
  { key: 'withImages', label: '有图' },
]

type Props = {
  filter: ArchiveFilter
  keyword: string
  onFilterChange: (filter: ArchiveFilter) => void
  onKeywordChange: (keyword: string) => void
}

export default function FilterBar({
  filter,
  keyword,
  onFilterChange,
  onKeywordChange,
}: Props) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-1 rounded-full border border-ink-700 bg-ink-900/70 p-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onFilterChange(tab.key)}
            aria-pressed={filter === tab.key}
            className={[
              'rounded-full px-3.5 py-1.5 text-sm transition-colors focus-ring',
              filter === tab.key
                ? 'bg-ember-500/20 text-ember-400'
                : 'text-slate-400 hover:text-slate-100',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="relative sm:w-72">
        <input
          type="search"
          value={keyword}
          onChange={(event) => onKeywordChange(event.target.value)}
          placeholder="搜索说说内容或评论…"
          aria-label="搜索说说内容或评论"
          className="w-full rounded-full border border-ink-700 bg-ink-900/70 px-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus-ring"
        />
      </div>
    </div>
  )
}

