import { ConversaChat } from '@/components/conversa-chat'

export default async function ConversaDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="h-[calc(100vh-7rem)]">
      <ConversaChat conversaId={id} />
    </div>
  )
}
