import { ComunicadoList } from '@/components/comunicado-list'

export default function ComunicadosPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Comunicados</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Disparo em massa de WhatsApp para a base, segmentado por cidade, status ou plano.
          </p>
        </div>
      </div>
      <ComunicadoList />
    </div>
  )
}
