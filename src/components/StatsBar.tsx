import { formatRange } from '../lib/format'
import type { ArchiveStats } from '../lib/archive'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card px-4 py-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-semibold text-slate-100">{value}</div>
    </div>
  )
}

export default function StatsBar({ stats }: { stats: ArchiveStats }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Stat label="说说总数" value={String(stats.total)} />
      <Stat label="已找回（原已删除）" value={String(stats.deleted)} />
      <Stat label="图片" value={String(stats.images)} />
      <Stat label="时间跨度" value={formatRange(stats.firstAt, stats.lastAt)} />
    </div>
  )
}

