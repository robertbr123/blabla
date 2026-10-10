import { ConversaChat } from '@/components/conversa-chat'

export default async function ConversaDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    // Topbar (3rem) + padding vertical do container: 2rem no celular, 2.5rem de
    // `sm` pra cima. `dvh` acompanha a barra do navegador no celular, então a
    // página não rola — só a lista de mensagens.
    <div className="h-[calc(100dvh-5rem)] sm:h-[calc(100dvh-5.5rem)]">
      <ConversaChat conversaId={id} />
    </div>
  )
}
