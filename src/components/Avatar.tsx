type Props = {
  src: string
  name: string
  size?: number
}

export default function Avatar({ src, name, size = 88 }: Props) {
  const dimension = { width: size, height: size }

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        style={dimension}
        className="rounded-full border border-ink-600 object-cover"
      />
    )
  }

  return (
    <div
      style={dimension}
      aria-hidden="true"
      className="grid place-items-center rounded-full border border-ink-600 bg-ink-800 text-2xl font-semibold text-ember-400"
    >
      {name.trim().slice(0, 1) || '·'}
    </div>
  )
}

