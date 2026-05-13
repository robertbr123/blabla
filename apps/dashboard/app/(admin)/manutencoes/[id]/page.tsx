import { ManutencaoDetail } from '@/components/manutencao-detail'

export default async function ManutencaoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <ManutencaoDetail id={id} />
    </div>
  )
}
