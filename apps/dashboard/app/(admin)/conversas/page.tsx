import { ConversaList } from '@/components/conversa-list'
import { PageHeader } from '@/components/noc/primitives'

export default function ConversasPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Conversas"
        description="Fila de atendimento: assuma as conversas aguardando e acompanhe as que estão com um humano."
      />
      <ConversaList />
    </div>
  )
}
