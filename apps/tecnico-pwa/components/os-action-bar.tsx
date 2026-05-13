'use client'
import { useRef, useState } from 'react'
import { Camera, CheckCircle2, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { GpsButton } from './gps-button'
import {
  useConcluirMyOs,
  useIniciarOs,
  useUpdateGps,
  useUploadFotoMy,
} from '@/lib/api/queries'
import type { OsOut } from '@/lib/api/types'

export function OsActionBar({ os }: { os: OsOut }) {
  const iniciar = useIniciarOs(os.id)
  const concluir = useConcluirMyOs(os.id)
  const upload = useUploadFotoMy(os.id)
  const updateGps = useUpdateGps()
  const fileRef = useRef<HTMLInputElement>(null)
  const [csat, setCsat] = useState('')
  const [comentario, setComentario] = useState('')
  const [pendingGps, setPendingGps] = useState<{ lat: number; lng: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleIniciar() {
    setError(null)
    try {
      let lat: number | undefined
      let lng: number | undefined
      if ('geolocation' in navigator) {
        try {
          const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              timeout: 10_000,
              enableHighAccuracy: true,
            }),
          )
          lat = pos.coords.latitude
          lng = pos.coords.longitude
        } catch {
          // ok — sem GPS
        }
      }
      await iniciar.mutateAsync({ lat: lat ?? null, lng: lng ?? null })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro')
    }
  }

  async function handleConcluir() {
    setError(null)
    try {
      await concluir.mutateAsync({
        csat: csat ? Number(csat) : undefined,
        comentario: comentario || undefined,
        lat: pendingGps?.lat,
        lng: pendingGps?.lng,
      })
      setCsat('')
      setComentario('')
      setPendingGps(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro')
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    try {
      await upload.mutateAsync(file)
    } catch (er) {
      setError(er instanceof Error ? er.message : 'Erro ao enviar foto')
    } finally {
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  if (os.status === 'concluida' || os.status === 'cancelada') {
    return null
  }

  if (os.status === 'pendente') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Iniciar atendimento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button
            onClick={handleIniciar}
            disabled={iniciar.isPending}
            className="w-full h-12"
          >
            <Play className="h-4 w-4" />
            {iniciar.isPending ? 'Iniciando…' : 'Iniciar OS'}
          </Button>
          <p className="text-xs text-muted-foreground">
            Vamos pedir permissão de GPS pra registrar onde você iniciou.
          </p>
        </CardContent>
      </Card>
    )
  }

  // status === 'em_andamento'
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Em atendimento</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="space-y-2">
          <Label>Foto</Label>
          <Input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFile}
            disabled={upload.isPending}
            className="h-11"
          />
          {upload.isPending && <p className="text-xs text-muted-foreground">Enviando…</p>}
        </div>

        <hr className="border-border" />

        <div className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Concluir atendimento</h3>
            <p className="text-xs text-muted-foreground">
              Capture o GPS final e (opcionalmente) registre o feedback do cliente.
            </p>
          </div>

          <GpsButton
            onCapture={async (lat, lng) => {
              setPendingGps({ lat, lng })
              await updateGps.mutateAsync({ lat, lng })
            }}
            label={
              pendingGps
                ? `GPS: ${pendingGps.lat.toFixed(5)}, ${pendingGps.lng.toFixed(5)}`
                : 'Capturar GPS final'
            }
          />

          <div>
            <Label htmlFor="csat">CSAT (1-5)</Label>
            <Input
              id="csat"
              type="number"
              inputMode="numeric"
              min={1}
              max={5}
              value={csat}
              onChange={(e) => setCsat(e.target.value)}
              className="h-11"
            />
          </div>

          <div>
            <Label htmlFor="comentario">Comentário do cliente</Label>
            <textarea
              id="comentario"
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <Button
            onClick={handleConcluir}
            disabled={concluir.isPending}
            className="w-full h-12"
          >
            <CheckCircle2 className="h-4 w-4" />
            {concluir.isPending ? 'Concluindo…' : 'Concluir OS'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
