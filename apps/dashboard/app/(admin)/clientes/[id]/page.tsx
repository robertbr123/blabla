import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { ClienteDetail } from '@/components/cliente-detail'

interface Props {
  params: Promise<{ id: string }>
}

export default async function ClienteDetailPage({ params }: Props) {
  const { id } = await params
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/clientes"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" /> Clientes
        </Link>
      </div>
      <ClienteDetail id={id} />
    </div>
  )
}
