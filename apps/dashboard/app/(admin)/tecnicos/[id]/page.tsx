import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { TecnicoDetail } from '@/components/tecnico-detail'

interface Props {
  params: Promise<{ id: string }>
}

export default async function TecnicoDetailPage({ params }: Props) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/tecnicos"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" /> Técnicos
        </Link>
      </div>
      <TecnicoDetail id={id} />
    </div>
  )
}
