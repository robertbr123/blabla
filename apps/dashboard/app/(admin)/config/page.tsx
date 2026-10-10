import { BotToggle } from '@/components/bot-toggle'
import { ConfigEditor } from '@/components/config-editor'
import { EvolutionStatus } from '@/components/evolution-status'
import { IndicacaoConfigEditor } from '@/components/indicacao-config-editor'
import { SgpConfigEditor } from '@/components/sgp-config-editor'
import { PageHeader } from '@/components/noc/primitives'

export default function ConfigPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Configurações"
        description="Editor de chaves de configuração (admin only)"
      />
      <EvolutionStatus />
      <BotToggle />
      <SgpConfigEditor />
      <IndicacaoConfigEditor />
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
