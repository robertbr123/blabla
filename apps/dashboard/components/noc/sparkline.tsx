/**
 * Sparkline: tendencia compacta dentro de um tile. Sem eixos nem tooltip —
 * o numero grande do tile e o valor; a linha so da a forma.
 * Linha 2px, area ~10% da mesma cor, ponto final de 8px com anel da superficie.
 */
export function Sparkline({
  values,
  color,
  label,
  height = 36,
}: {
  values: number[]
  /** Cor CSS da serie (ex.: 'var(--chart-1)'). */
  color: string
  /** Descricao pra leitor de tela ("Mensagens por dia, ultimos 7 dias"). */
  label: string
  height?: number
}) {
  if (values.length < 2) return <div style={{ height }} aria-hidden />
  const W = 200
  const H = height
  const PAD = 5
  const max = Math.max(...values)
  const min = Math.min(...values)
  const span = max - min || 1
  const step = (W - PAD * 2) / (values.length - 1)
  const pts = values.map((v, i) => ({
    x: PAD + i * step,
    y: PAD + (H - PAD * 2) * (1 - (v - min) / span),
  }))
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const first = pts[0]
  const last = pts[pts.length - 1]
  if (!first || !last) return null
  const area = `${line} L${last.x.toFixed(1)},${H} L${first.x.toFixed(1)},${H} Z`
  return (
    // O SVG estica na largura (preserveAspectRatio none); o ponto final e um
    // elemento HTML por cima pra continuar redondo.
    <div className="relative w-full" style={{ height }} role="img" aria-label={label}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="block h-full w-full"
        aria-hidden
      >
        <path d={area} fill={color} fillOpacity={0.1} />
        <path
          d={line}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <span
        aria-hidden
        className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card"
        style={{
          left: `${(last.x / W) * 100}%`,
          top: `${(last.y / H) * 100}%`,
          backgroundColor: color,
        }}
      />
    </div>
  )
}
