import { ConversaList } from '@/components/conversa-list'

export default function ConversasPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Conversas</h1>
        <p className="text-sm text-muted-foreground">
          Atenda conversas em status &ldquo;aguardando&rdquo; ou acompanhe conversas humanas
        </p>
      </div>
      <ConversaList />
    </div>
  )
}
