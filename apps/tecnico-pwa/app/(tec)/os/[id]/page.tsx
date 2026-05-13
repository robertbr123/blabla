'use client'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { OsActionBar } from '@/components/os-action-bar'
import { OsDetailView } from '@/components/os-detail-view'
import { useMyOsDetail } from '@/lib/api/queries'

export default function OsPage() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const { data, isLoading, error } = useMyOsDetail(id)

  return (
    <div className="space-y-4">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Minhas OS
      </Link>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <>
          <OsDetailView os={data} />
          <OsActionBar os={data} />
        </>
      )}
    </div>
  )
}
