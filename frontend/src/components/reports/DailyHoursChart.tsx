import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { daysBetween, formatDay, formatDuration } from '@/lib/time'

const PLOT_HEIGHT = 160
const TOP = 12
const AXIS_BAND = 24 // altura reservada a las etiquetas del eje X (dentro del SVG, sin recortes)
const LEFT = 40 // ancho de las etiquetas del eje Y
const MAX_BAR = 24
const MAX_DAYS = 62

// "Horas por día" del panel: columnas de una sola serie (un color, sin leyenda: el título ya
// dice qué es). Pasar el ratón o el foco del teclado por un día muestra sus horas; "Ver como
// tabla" da los mismos valores sin depender del tooltip.
export function DailyHoursChart({
  from,
  to,
  byDay,
  dimmed,
}: {
  from: string
  to: string
  byDay: { day: string; total_seconds: number }[]
  dimmed: boolean
}) {
  const [width, ref] = useElementWidth<HTMLDivElement>()
  const [hovered, setHovered] = useState<number | null>(null)
  const [asTable, setAsTable] = useState(false)
  const days = daysBetween(from, to)
  // La API solo devuelve días con horas: los demás valen 0.
  const secondsByDay = new Map(byDay.map((d) => [d.day, d.total_seconds]))
  const values = days.map((day) => (secondsByDay.get(day) ?? 0) / 3600)

  if (days.length > MAX_DAYS) {
    return (
      <p className="text-sm text-muted-foreground">
        La gráfica por días se muestra para rangos de hasta {MAX_DAYS} días.
      </p>
    )
  }

  const { max, ticks } = niceScale(Math.max(...values, 0))
  const plotWidth = Math.max(width - LEFT, 0)
  const band = plotWidth / days.length
  const barWidth = Math.min(MAX_BAR, band * 0.6)
  const y = (hours: number) => TOP + PLOT_HEIGHT - (hours / max) * PLOT_HEIGHT
  // Etiquetas del eje X con al menos ~28px entre ellas: con muchos días, una de cada n.
  const labelEvery = Math.max(1, Math.ceil(28 / Math.max(band, 1)))

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Horas por día</h3>
        <Button size="sm" variant="ghost" onClick={() => setAsTable(!asTable)}>
          {asTable ? 'Ver gráfica' : 'Ver como tabla'}
        </Button>
      </div>

      {asTable ? (
        <table className="w-full text-sm">
          <tbody>
            {days.map((day, i) => (
              <tr key={day} className="border-b">
                <td className="py-1 capitalize">{formatDay(day)}</td>
                <td className="py-1 text-right font-mono tabular-nums">
                  {values[i] ? formatDuration(values[i] * 3600) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div ref={ref} className={`relative transition-opacity ${dimmed ? 'opacity-60' : ''}`}>
          {width > 0 && (
            <svg
              width={width}
              height={TOP + PLOT_HEIGHT + AXIS_BAND}
              role="img"
              aria-label="Horas por día del periodo"
              onPointerLeave={() => setHovered(null)}
            >
              {/* Cuadrícula: líneas finas y continuas, un tono por encima del fondo. */}
              {ticks.map((tick) => (
                <g key={tick}>
                  <line
                    x1={LEFT}
                    x2={width}
                    y1={y(tick)}
                    y2={y(tick)}
                    stroke="var(--border)"
                    strokeWidth={1}
                  />
                  <text
                    x={LEFT - 6}
                    y={y(tick)}
                    textAnchor="end"
                    dominantBaseline="middle"
                    className="fill-muted-foreground text-[11px] tabular-nums"
                  >
                    {tick} h
                  </text>
                </g>
              ))}
              {days.map((day, i) => {
                const x = LEFT + i * band
                const barX = x + (band - barWidth) / 2
                const top = y(values[i])
                const height = TOP + PLOT_HEIGHT - top
                return (
                  <g key={day}>
                    {values[i] > 0 && (
                      <path
                        d={roundedTopBar(barX, top, barWidth, height, Math.min(4, barWidth / 2, height))}
                        fill="var(--series-1)"
                        opacity={hovered === null || hovered === i ? 1 : 0.55}
                      />
                    )}
                    {i % labelEvery === 0 && (
                      <text
                        x={x + band / 2}
                        y={TOP + PLOT_HEIGHT + 16}
                        textAnchor="middle"
                        className="fill-muted-foreground text-[11px] tabular-nums"
                      >
                        {Number(day.slice(8))}
                      </text>
                    )}
                    {/* Zona de hover/foco: toda la columna del día, no solo la barra pintada. */}
                    <rect
                      x={x}
                      y={TOP}
                      width={band}
                      height={PLOT_HEIGHT + AXIS_BAND}
                      fill="transparent"
                      tabIndex={0}
                      aria-label={`${formatDay(day)}: ${formatDuration(values[i] * 3600)} h`}
                      className="outline-none"
                      onPointerMove={() => setHovered(i)}
                      onFocus={() => setHovered(i)}
                      onBlur={() => setHovered(null)}
                    />
                  </g>
                )
              })}
              {/* Línea base, algo más marcada que la cuadrícula. */}
              <line
                x1={LEFT}
                x2={width}
                y1={TOP + PLOT_HEIGHT}
                y2={TOP + PLOT_HEIGHT}
                stroke="var(--muted-foreground)"
                strokeOpacity={0.5}
                strokeWidth={1}
              />
            </svg>
          )}
          {hovered !== null && width > 0 && (
            <div
              className="pointer-events-none absolute -translate-x-1/2 -translate-y-full rounded-md border bg-popover px-2 py-1 text-xs shadow-sm"
              style={{
                left: Math.min(Math.max(LEFT + (hovered + 0.5) * band, 60), width - 60),
                top: Math.max(y(values[hovered]) - 6, 40),
              }}
            >
              <div className="font-semibold">{formatDuration(values[hovered] * 3600)} h</div>
              <div className="text-muted-foreground capitalize">{formatDay(days[hovered])}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Columna con las esquinas de arriba redondeadas y la base recta (apoyada en el eje).
function roundedTopBar(x: number, y: number, w: number, h: number, r: number): string {
  return [
    `M${x},${y + h}`,
    `V${y + r}`,
    `Q${x},${y} ${x + r},${y}`,
    `H${x + w - r}`,
    `Q${x + w},${y} ${x + w},${y + r}`,
    `V${y + h}`,
    'Z',
  ].join(' ')
}

// Máximo y marcas del eje Y en números redondos de horas (1, 2, 5, 10...).
function niceScale(maxValue: number): { max: number; ticks: number[] } {
  if (maxValue <= 0) return { max: 1, ticks: [0, 1] }
  const steps = [0.5, 1, 2, 4, 5, 10, 20, 25, 50, 100]
  const step = steps.find((s) => maxValue / s <= 4) ?? Math.ceil(maxValue / 4)
  const max = Math.ceil(maxValue / step) * step
  const ticks: number[] = []
  for (let t = 0; t <= max + 1e-9; t += step) ticks.push(Number(t.toFixed(2)))
  return { max, ticks }
}

// Ancho real del contenedor (y se actualiza al redimensionar): el SVG se dibuja a ese ancho
// en vez de escalarse, para que el texto no se deforme.
function useElementWidth<T extends HTMLElement>(): [number, (node: T | null) => void] {
  const [width, setWidth] = useState(0)
  const observer = useRef<ResizeObserver | null>(null)
  const ref = useCallback((node: T | null) => {
    observer.current?.disconnect()
    if (!node) return
    observer.current = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.current.observe(node)
  }, [])
  useEffect(() => () => observer.current?.disconnect(), [])
  return [width, ref]
}
