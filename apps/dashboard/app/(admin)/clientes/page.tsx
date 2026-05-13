import { ClienteList } from '@/components/cliente-list'

export default function ClientesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Clientes</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Clientes sincronizados via SGP. Dados PII disponíveis no detalhe.
        </p>
      </div>
      <ClienteList />
    </div>
  )
}
