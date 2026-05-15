'use client'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

interface HealthOut {
  status: string
  checks: Record<string, string>
}

export function EvolutionStatus() {
  const { data, isFetching, refetch } = useQuery({
    queryKey: ['healthz'],
    queryFn: () => apiFetch<HealthOut>('/healthz'),
    refetchInterval: 30_000,
  })

  const evoStatus = data?.checks?.evolution ?? null

  const isOk = evoStatus === 'ok'
  const isLoading = isFetching && !data

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-semibold">Evolution API (WhatsApp)</CardTitle>
        <Button variant="ghost" size="icon" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent className="flex items-center gap-3">
        {isLoading ? (
          <Badge variant="outline">Verificando...</Badge>
        ) : evoStatus === null ? (
          <Badge variant="outline">Indisponível</Badge>
        ) : (
          <>
            <span
              className={`h-3 w-3 rounded-full ${isOk ? 'bg-green-500' : 'bg-red-500'}`}
            />
            <Badge variant={isOk ? 'default' : 'destructive'}>
              {isOk ? 'Conectado' : evoStatus}
            </Badge>
          </>
        )}
      </CardContent>
    </Card>
  )
}
