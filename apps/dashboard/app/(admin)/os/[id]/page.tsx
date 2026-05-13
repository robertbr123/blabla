import { OsDetail } from '@/components/os-detail'

export default async function OsDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <OsDetail id={id} />
    </div>
  )
}
