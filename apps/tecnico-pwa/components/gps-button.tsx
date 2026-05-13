'use client'
import { useState } from 'react'
import { MapPin } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface GpsButtonProps {
  onCapture: (lat: number, lng: number) => void | Promise<void>
  label?: string
  disabled?: boolean
}

export function GpsButton({ onCapture, label = 'Capturar GPS', disabled }: GpsButtonProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleClick() {
    if (!('geolocation' in navigator)) {
      setError('GPS não disponível neste dispositivo')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          timeout: 15_000,
          maximumAge: 30_000,
          enableHighAccuracy: true,
        }),
      )
      await onCapture(pos.coords.latitude, pos.coords.longitude)
    } catch (e) {
      const msg =
        e instanceof GeolocationPositionError
          ? `Erro GPS: ${e.message}`
          : e instanceof Error
            ? e.message
            : 'Falha ao capturar GPS'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-1">
      <Button
        type="button"
        variant="outline"
        onClick={handleClick}
        disabled={busy || disabled}
        className="w-full h-11"
      >
        <MapPin className="h-4 w-4" />
        {busy ? 'Capturando…' : label}
      </Button>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
