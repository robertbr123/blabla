'use client'
import { useEffect, useState } from 'react'
import { ImageOff, X } from 'lucide-react'
import type { OsFoto } from '@/lib/api/types'
import { getAccessToken } from '@/lib/api/token'

/**
 * Galeria de fotos da OS. As fotos sao protegidas por token, entao
 * usamos fetch com Authorization + criamos object URL pra exibir.
 */
export function FotosGaleria({
  osId,
  fotos,
}: {
  osId: string
  fotos: OsFoto[]
}) {
  const [openIdx, setOpenIdx] = useState<number | null>(null)
  return (
    <>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {fotos.map((f, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setOpenIdx(i)}
            className="group relative aspect-square overflow-hidden rounded-md border bg-muted transition hover:border-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            title={new Date(f.ts).toLocaleString('pt-BR')}
            aria-label={`Ampliar foto ${i + 1}`}
          >
            <ProtectedImage
              src={`/api/v1/os/${osId}/foto/${i}`}
              alt={`Foto ${i + 1}`}
            />
          </button>
        ))}
      </div>

      {openIdx !== null && (
        <Lightbox
          src={`/api/v1/os/${osId}/foto/${openIdx}`}
          info={`Foto ${openIdx + 1} de ${fotos.length} · ${new Date(fotos[openIdx].ts).toLocaleString('pt-BR')}`}
          onClose={() => setOpenIdx(null)}
        />
      )}
    </>
  )
}

/** Lê uma imagem protegida com Authorization e renderiza via blob URL. */
function ProtectedImage({ src, alt }: { src: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let canceled = false
    let createdUrl: string | null = null
    ;(async () => {
      try {
        const token = getAccessToken()
        const res = await fetch(src, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          credentials: 'include',
        })
        if (!res.ok) throw new Error(String(res.status))
        const blob = await res.blob()
        if (canceled) return
        createdUrl = URL.createObjectURL(blob)
        setUrl(createdUrl)
      } catch {
        if (!canceled) setError(true)
      }
    })()
    return () => {
      canceled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [src])

  if (error) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-[10px] text-destructive">
        <ImageOff aria-hidden className="h-3.5 w-3.5" />
        Erro
      </div>
    )
  }
  if (!url) {
    return <div aria-hidden className="h-full w-full animate-pulse bg-muted" />
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} className="h-full w-full object-cover" />
}

function Lightbox(props: {
  src: string
  info: string
  onClose: () => void
}) {
  const { onClose } = props
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Foto ampliada"
      className="fixed inset-0 z-[80] flex items-center justify-center bg-background/90 p-4 backdrop-blur-sm"
      onClick={props.onClose}
    >
      <button
        type="button"
        onClick={props.onClose}
        className="absolute right-4 top-4 rounded-md border bg-card p-2 text-foreground transition-colors hover:bg-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Fechar"
        title="Fechar"
      >
        <X className="h-5 w-5" />
      </button>
      <div
        className="max-h-[90vh] max-w-[90vw]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="overflow-hidden rounded-lg border bg-card">
          <ProtectedImage src={props.src} alt="Foto ampliada" />
        </div>
        <p className="num mt-2 text-center text-xs text-muted-foreground">{props.info}</p>
      </div>
    </div>
  )
}
