'use client'
import { useState } from 'react'
import { DollarSign, Trophy } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useProdutividade } from '@/lib/api/queries'

function currentMonthStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function fmtR(v: number): string {
  return v.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  })
}

export default function ProdutividadePage() {
  const [mes, setMes] = useState(currentMonthStr())
  const { data, isLoading, error } = useProdutividade(mes)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Trophy className="h-6 w-6" /> Produtividade & Comissão
          </h1>
          <p className="text-sm text-muted-foreground">
            Ranking de técnicos + cálculo de comissão por mês.
          </p>
        </div>
        <div className="w-44">
          <Label htmlFor="mes">Mês</Label>
          <Input
            id="mes"
            type="month"
            value={mes}
            onChange={(e) => setMes(e.target.value)}
          />
        </div>
      </div>

      {data && (
        <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
          <strong>Regras de comissão deste mês:</strong>{' '}
          {fmtR(data.config.valor_por_os)} por OS · bônus CSAT 5:{' '}
          {fmtR(data.config.bonus_csat_5)} · bônus CSAT 4:{' '}
          {fmtR(data.config.bonus_csat_4)}
          {data.config.valor_por_os === 0 &&
            data.config.bonus_csat_5 === 0 &&
            data.config.bonus_csat_4 === 0 && (
              <div className="mt-1 text-amber-700">
                ⚠️ Comissão zerada — configure em /api/v1/config:
                <code className="font-mono"> comissao.valor_por_os</code>,{' '}
                <code className="font-mono">comissao.bonus_csat_5</code>,{' '}
                <code className="font-mono">comissao.bonus_csat_4</code>
              </div>
            )}
        </div>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {error && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Erro ao carregar'}
        </p>
      )}

      {data && (
        <div className="overflow-x-auto rounded-md border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-3">Técnico</th>
                <th className="px-3 py-3 text-right">OS</th>
                <th className="px-3 py-3 text-right">CSAT 5</th>
                <th className="px-3 py-3 text-right">CSAT 4</th>
                <th className="px-3 py-3 text-right">Sem CSAT</th>
                <th className="px-3 py-3 text-right">CSAT médio</th>
                <th className="px-3 py-3 text-right">Tempo médio</th>
                <th className="px-3 py-3 text-right">Base</th>
                <th className="px-3 py-3 text-right">Bônus</th>
                <th className="px-3 py-3 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.tecnicos.length === 0 && (
                <tr>
                  <td colSpan={10} className="p-6 text-center text-muted-foreground">
                    Sem técnicos ativos.
                  </td>
                </tr>
              )}
              {data.tecnicos.map((t, idx) => (
                <tr key={t.tecnico_id} className="border-b last:border-b-0 hover:bg-muted/50">
                  <td className="px-3 py-3 font-medium">
                    <div className="flex items-center gap-2">
                      {idx < 3 && t.os_concluidas > 0 && (
                        <Badge
                          variant={idx === 0 ? 'default' : 'outline'}
                          className="text-[10px]"
                        >
                          {idx + 1}º
                        </Badge>
                      )}
                      {t.nome}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-right">{t.os_concluidas}</td>
                  <td className="px-3 py-3 text-right text-green-700">{t.os_csat_5}</td>
                  <td className="px-3 py-3 text-right text-blue-700">{t.os_csat_4}</td>
                  <td className="px-3 py-3 text-right text-muted-foreground">
                    {t.os_sem_csat}
                  </td>
                  <td className="px-3 py-3 text-right">
                    {t.csat_avg !== null ? t.csat_avg.toFixed(2) : '—'}
                  </td>
                  <td className="px-3 py-3 text-right text-muted-foreground">
                    {t.tempo_medio_min !== null ? `${t.tempo_medio_min} min` : '—'}
                  </td>
                  <td className="px-3 py-3 text-right text-muted-foreground">
                    {fmtR(t.comissao_base)}
                  </td>
                  <td className="px-3 py-3 text-right text-muted-foreground">
                    {fmtR(t.comissao_bonus)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <span className="inline-flex items-center gap-1 font-semibold">
                      <DollarSign className="h-3 w-3" />
                      {fmtR(t.comissao_total)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
            {data.tecnicos.length > 0 && (
              <tfoot className="border-t bg-muted/30">
                <tr>
                  <td className="px-3 py-3 font-semibold">Total geral</td>
                  <td className="px-3 py-3 text-right font-semibold">
                    {data.tecnicos.reduce((s, t) => s + t.os_concluidas, 0)}
                  </td>
                  <td colSpan={6} />
                  <td className="px-3 py-3 text-right font-semibold">
                    {fmtR(
                      data.tecnicos.reduce((s, t) => s + t.comissao_bonus, 0),
                    )}
                  </td>
                  <td className="px-3 py-3 text-right font-semibold">
                    {fmtR(
                      data.tecnicos.reduce((s, t) => s + t.comissao_total, 0),
                    )}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </div>
  )
}
