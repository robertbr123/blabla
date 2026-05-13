import { ConfigEditor } from '@/components/config-editor'

export default function ConfigPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Configurações</h1>
        <p className="text-sm text-muted-foreground">
          Editor de chaves de configuração (admin only)
        </p>
      </div>
      <ConfigEditor />
    </div>
  )
}
