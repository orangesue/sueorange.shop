import { useCallback, useEffect } from 'react'

type Props = {
  images: string[]
  index: number
  onClose: () => void
  onIndexChange: (index: number) => void
}

export default function Lightbox({ images, index, onClose, onIndexChange }: Props) {
  const hasPrev = index > 0
  const hasNext = index < images.length - 1

  const go = useCallback(
    (delta: number) => {
      const next = index + delta
      if (next < 0 || next >= images.length) return
      onIndexChange(next)
    },
    [index, images.length, onIndexChange],
  )

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
      if (event.key === 'ArrowLeft') go(-1)
      if (event.key === 'ArrowRight') go(1)
    }

    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [go, onClose])

  if (images.length === 0) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="图片预览"
      onClick={onClose}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-black/85 p-4 backdrop-blur-sm"
    >
      <img
        src={images[index]}
        alt=""
        referrerPolicy="no-referrer"
        onClick={(event) => event.stopPropagation()}
        className="max-h-[80vh] max-w-full rounded-xl object-contain shadow-2xl"
      />

      <div
        className="flex items-center gap-3 text-sm text-slate-300"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={!hasPrev}
          className="rounded-full border border-ink-600 px-3 py-1 disabled:opacity-40 focus-ring"
        >
          上一张
        </button>
        <span className="tabular-nums">
          {index + 1} / {images.length}
        </span>
        <button
          type="button"
          onClick={() => go(1)}
          disabled={!hasNext}
          className="rounded-full border border-ink-600 px-3 py-1 disabled:opacity-40 focus-ring"
        >
          下一张
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-full border border-ink-600 px-3 py-1 focus-ring"
        >
          关闭
        </button>
      </div>
    </div>
  )
}
