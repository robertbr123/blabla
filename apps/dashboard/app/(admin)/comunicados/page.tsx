import { ComunicadoList } from '@/components/comunicado-list'
import { PageHeader } from '@/components/noc/primitives'

export default function ComunicadosPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Comunicados"
        description="Disparo em massa de WhatsApp para a base, segmentado por cidade, status ou plano."
      />
      <ComunicadoList />
    </div>
  )
}
