import { BotToggle } from '@/components/bot-toggle'
import { ConfigEditor } from '@/components/config-editor'
import { EvolutionStatus } from '@/components/evolution-status'
import { SgpConfigEditor } from '@/components/sgp-config-editor'

export default function ConfigPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Configurações</h1>
        <p className="text-sm text-muted-foreground">
          Editor de chaves de configuração (admin only)
        </p>
      </div>
      <EvolutionStatus />
      <BotToggle />
      <SgpConfigEditor />
      <div>
        <h2 className="text-lg font-semibold">Editor genérico (k/v)</h2>
        <p className="text-sm text-muted-foreground mb-3">
          Qualquer chave em <code>config</code> — JSON bruto.
        </p>
        <ConfigEditor />
      </div>
    </div>
  )
}
