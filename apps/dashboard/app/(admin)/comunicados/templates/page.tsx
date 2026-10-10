import { ComunicadoTemplates } from '@/components/comunicado-templates'
import { PageHeader } from '@/components/noc/primitives'

export default function TemplatesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Templates"
        description="Sincronize os templates aprovados da Meta ou cadastre manualmente."
      />
      <ComunicadoTemplates />
    </div>
  )
}
