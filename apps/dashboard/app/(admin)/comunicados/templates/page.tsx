import { ComunicadoTemplates } from '@/components/comunicado-templates'

export default function TemplatesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Templates</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sincronize os templates aprovados da Meta ou cadastre manualmente.
        </p>
      </div>
      <ComunicadoTemplates />
    </div>
  )
}
