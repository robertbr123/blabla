import { ClienteList } from '@/components/cliente-list'
import { PageHeader } from '@/components/noc/primitives'

export default function ClientesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Clientes"
        description="Clientes sincronizados via SGP. Dados PII disponíveis no detalhe."
      />
      <ClienteList />
    </div>
  )
}
