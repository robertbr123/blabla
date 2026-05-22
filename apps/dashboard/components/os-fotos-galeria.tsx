'use client'
import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
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
            onClick={() => setOpenIdx(i)}
            className="group relative aspect-square overflow-hidden rounded-md border border-zinc-200 bg-zinc-100 transition hover:opacity-90"
            title={new Date(f.ts).toLocaleString('pt-BR')}
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
      <div className="flex h-full w-full items-center justify-center text-[10px] text-red-500">
        Erro
      </div>
    )
  }
  if (!url) {
    return <div className="h-full w-full animate-pulse bg-zinc-200" />
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} className="h-full w-full object-cover" />
}

function Lightbox(props: {
  src: string
  info: string
  onClose: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/85 p-4"
      onClick={props.onClose}
    >
      <button
        onClick={props.onClose}
        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        aria-label="Fechar"
      >
        <X className="h-5 w-5" />
      </button>
      <div
        className="max-h-[90vh] max-w-[90vw]"
        onClick={(e) => e.stopPropagation()}
      >
        <ProtectedImage src={props.src} alt="Foto ampliada" />
        <p className="mt-2 text-center text-xs text-white/70">{props.info}</p>
      </div>
    </div>
  )
}
