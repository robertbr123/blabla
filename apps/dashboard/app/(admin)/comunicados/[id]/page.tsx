import { ComunicadoDetail } from '@/components/comunicado-detail'

export default async function CampanhaDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <ComunicadoDetail id={id} />
    </div>
  )
}
