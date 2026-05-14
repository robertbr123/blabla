'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useRankingTecnicos, downloadRankingCsv } from '@/lib/api/queries'

function formatTempo(min: number | null): string {
  if (min === null) return '—'
  const h = Math.floor(min / 60)
  const m = min % 60
  return h > 0 ? `${h}h${m.toString().padStart(2, '0')}` : `${m}min`
}

function medalha(pos: number): string {
  if (pos === 0) return '🥇'
  if (pos === 1) return '🥈'
  if (pos === 2) return '🥉'
  return String(pos + 1)
}

export default function RankingTecnicosPage() {
  const now = new Date()
  const defaultMes = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const [mes, setMes] = useState(defaultMes)

  const { data, isLoading, error } = useRankingTecnicos(mes)

  const totalOs = (data ?? []).reduce((sum, t) => sum + t.os_concluidas, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ranking de Técnicos</h1>
        <p className="text-sm text-muted-foreground">
          OS concluídas, CSAT médio e tempo médio por técnico no período
        </p>
      </div>

      <div className="flex items-center gap-3">
        <input
          type="month"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        />
        <Button variant="outline" onClick={() => downloadRankingCsv(mes)}>
          ⬇️ Exportar CSV
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && <p className="text-sm text-destructive">Erro ao carregar ranking</p>}

      {data && (
        <>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left">#</th>
                  <th className="px-4 py-2 text-left">Técnico</th>
                  <th className="px-4 py-2 text-center">OS Concluídas</th>
                  <th className="px-4 py-2 text-center">CSAT Médio</th>
                  <th className="px-4 py-2 text-center">Tempo Médio</th>
                </tr>
              </thead>
              <tbody>
                {data.map((tec, i) => (
                  <tr
                    key={tec.tecnico_id}
                    className={`border-t ${i === 0 ? 'bg-yellow-50' : ''}`}
                  >
                    <td className="px-4 py-3 font-medium">{medalha(i)}</td>
                    <td className="px-4 py-3 font-medium">{tec.nome}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          tec.os_concluidas >= 30
                            ? 'bg-green-100 text-green-800'
                            : tec.os_concluidas >= 10
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {tec.os_concluidas}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {tec.csat_avg !== null ? `⭐ ${tec.csat_avg.toFixed(1)}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-center text-muted-foreground">
                      {formatTempo(tec.tempo_medio_min)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-right text-xs text-muted-foreground">
            Total: {totalOs} OS concluídas no período
          </p>
        </>
      )}
    </div>
  )
}
