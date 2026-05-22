'use client'
import { ExternalLink, MapPin, Flag } from 'lucide-react'

interface Coord {
  lat: number
  lng: number
}

/**
 * Mapa OpenStreetMap embed (sem deps JS).
 * Mostra marker(s) e bbox calculado dos pontos disponíveis.
 */
export function OsMapa(props: { inicio: Coord | null; fim: Coord | null }) {
  const pts = [props.inicio, props.fim].filter(Boolean) as Coord[]
  if (pts.length === 0) return null

  // bbox com padding (~150m em torno do ponto único, ou bbox dos dois pontos)
  const pad = 0.001
  const lats = pts.map((p) => p.lat)
  const lngs = pts.map((p) => p.lng)
  const minLat = Math.min(...lats) - pad
  const maxLat = Math.max(...lats) + pad
  const minLng = Math.min(...lngs) - pad
  const maxLng = Math.max(...lngs) + pad

  // OSM permite só 1 marker via querystring. Usamos o último (fim > inicio).
  const markerPt = props.fim ?? props.inicio
  const markerStr = markerPt
    ? `&marker=${markerPt.lat}%2C${markerPt.lng}`
    : ''

  const osmEmbed = `https://www.openstreetmap.org/export/embed.html?bbox=${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}&layer=mapnik${markerStr}`
  const gmaps = `https://www.google.com/maps/search/?api=1&query=${markerPt?.lat}%2C${markerPt?.lng}`
  const waze = `https://waze.com/ul?ll=${markerPt?.lat}%2C${markerPt?.lng}&navigate=yes`

  return (
    <div className="space-y-2">
      <div className="aspect-video w-full overflow-hidden rounded-md border border-zinc-200">
        <iframe
          src={osmEmbed}
          className="h-full w-full"
          style={{ border: 0 }}
          loading="lazy"
          title="Mapa da visita"
        />
      </div>
      <div className="space-y-1 text-xs">
        {props.inicio && (
          <div className="flex items-center gap-1.5 text-zinc-600">
            <MapPin className="h-3 w-3 text-emerald-600" />
            <span className="font-medium">Início:</span>
            <code className="font-mono text-[11px]">
              {props.inicio.lat.toFixed(6)}, {props.inicio.lng.toFixed(6)}
            </code>
          </div>
        )}
        {props.fim && (
          <div className="flex items-center gap-1.5 text-zinc-600">
            <Flag className="h-3 w-3 text-rose-600" />
            <span className="font-medium">Fim:</span>
            <code className="font-mono text-[11px]">
              {props.fim.lat.toFixed(6)}, {props.fim.lng.toFixed(6)}
            </code>
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <a
          href={gmaps}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-xs font-semibold hover:bg-zinc-50"
        >
          <ExternalLink className="h-3 w-3" />
          Google Maps
        </a>
        <a
          href={waze}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-xs font-semibold hover:bg-zinc-50"
        >
          <ExternalLink className="h-3 w-3" />
          Waze
        </a>
      </div>
    </div>
  )
}
