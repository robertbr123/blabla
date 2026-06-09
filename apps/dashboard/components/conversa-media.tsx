'use client'
import { useEffect, useState } from 'react'
import { getAccessToken } from '@/lib/api/token'

export type MediaKind = 'image' | 'audio' | 'video' | 'document'

/**
 * Normaliza o `media_type` da mensagem num tipo de render. Inbound (cliente)
 * guarda o "kind" curto ("image"/"audio"/...); outbound (atendente) guarda o
 * mime completo ("image/jpeg"). Esta funcao cobre os dois.
 */
export function mediaKind(mt: string | null | undefined): MediaKind | null {
  if (!mt) return null
  const t = mt.toLowerCase()
  if (t.startsWith('image')) return 'image'
  if (t.startsWith('audio')) return 'audio'
  if (t.startsWith('video')) return 'video'
  if (t === 'document' || t.startsWith('application')) return 'document'
  return null
}

/**
 * Busca a midia protegida (Bearer token) e renderiza via object URL conforme o
 * tipo. Mesmo padrao do `ProtectedImage` da galeria de fotos de OS.
 */
export function ConversaMedia({
  src,
  kind,
}: {
  src: string
  kind: MediaKind
}) {
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
      <div className="text-xs italic opacity-70">
        Mídia ainda não disponível
      </div>
    )
  }
  if (!url) {
    return <div className="h-24 w-40 animate-pulse rounded bg-black/10" />
  }

  if (kind === 'image') {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt="imagem enviada"
        className="max-h-64 max-w-full cursor-pointer rounded"
        onClick={() => window.open(url, '_blank')}
      />
    )
  }
  if (kind === 'audio') {
    return <audio controls src={url} className="w-full max-w-[16rem]" />
  }
  if (kind === 'video') {
    return <video controls src={url} className="max-h-64 max-w-full rounded" />
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      download
      className="text-sm underline"
    >
      Baixar arquivo
    </a>
  )
}
