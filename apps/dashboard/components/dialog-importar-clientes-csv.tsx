'use client'
import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useImportClientesCsv } from '@/lib/api/queries'
import type { ImportResultOut } from '@/lib/api/types'

interface Props {
  onClose: () => void
}

export function DialogImportarClientesCsv({ onClose }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [dryRun, setDryRun] = useState(true)
  const [markAsSynced, setMarkAsSynced] = useState(true)
  const [resultado, setResultado] = useState<ImportResultOut | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const importar = useImportClientesCsv()

  async function submit() {
    setErro(null)
    if (!file) return setErro('Selecione um arquivo CSV.')
    if (file.size > 10 * 1024 * 1024) return setErro('Arquivo excede 10MB.')
    try {
      const r = await importar.mutateAsync({ file, dryRun, markAsSynced })
      setResultado(r)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao importar')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-4">
      <div className="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg space-y-4 mx-4">
        <div>
          <h2 className="text-lg font-semibold">Importar do MySQL antigo</h2>
          <p className="text-xs text-muted-foreground">
            Faça upload de um CSV exportado do site MySQL. Colunas esperadas:
            cpf, name, dob, phone, cep, address, number, complement,
            neighborhood, city, state, plan, pppoe_user, pppoe_pass, due_date,
            installer, serial, contrato, observation, latitude, longitude,
            location_accuracy, registration_date.
          </p>
        </div>

        {!resultado && (
          <>
            <div>
              <Label>Arquivo CSV (max 10MB)</Label>
              <div className="mt-1 flex items-center gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  className="gap-2"
                >
                  <Upload className="h-4 w-4" />
                  Escolher arquivo
                </Button>
                {file && (
                  <span className="text-xs text-muted-foreground">
                    {file.name} ({Math.round(file.size / 1024)} KB)
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="text-sm font-medium">Modo simulação (dry-run)</p>
                <p className="text-xs text-muted-foreground">
                  Mostra o que seria importado sem gravar nada. Recomendado pra
                  testar primeiro.
                </p>
              </div>
              <Switch checked={dryRun} onCheckedChange={setDryRun} />
            </div>

            <div className="flex items-center justify-between rounded-md border p-3">
              <div>
                <p className="text-sm font-medium">Marcar como sincronizado</p>
                <p className="text-xs text-muted-foreground">
                  Esses clientes já estão no SGP (vieram do site antigo). Use
                  data de registro como timestamp de sincronização.
                </p>
              </div>
              <Switch checked={markAsSynced} onCheckedChange={setMarkAsSynced} />
            </div>

            {erro && (
              <p className="text-sm text-destructive whitespace-pre-wrap">{erro}</p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={onClose}>
                Cancelar
              </Button>
              <Button onClick={submit} disabled={importar.isPending || !file}>
                {importar.isPending
                  ? 'Importando…'
                  : dryRun
                    ? 'Simular'
                    : 'Importar de verdade'}
              </Button>
            </div>
          </>
        )}

        {resultado && (
          <>
            <div className="rounded-md border bg-muted/30 p-4 space-y-2">
              <p className="font-semibold">
                {dryRun ? 'Simulação concluída' : 'Importação concluída'}
              </p>
              <div className="grid grid-cols-3 gap-2 text-center">
                <ResultStat
                  label="Inseridos"
                  value={resultado.inserted}
                  color="text-emerald-700"
                />
                <ResultStat
                  label="Atualizados"
                  value={resultado.updated}
                  color="text-blue-700"
                />
                <ResultStat
                  label="Pulados"
                  value={resultado.skipped}
                  color="text-amber-700"
                />
              </div>
            </div>

            {resultado.errors.length > 0 && (
              <div className="rounded-md border border-amber-300 bg-amber-50 p-3 max-h-40 overflow-y-auto">
                <p className="text-xs font-semibold mb-1 text-amber-900">
                  {resultado.errors.length} erro(s) — mostrando primeiros 10:
                </p>
                <ul className="space-y-0.5 text-[11px] text-amber-900 font-mono">
                  {resultado.errors.slice(0, 10).map((e, i) => (
                    <li key={i}>· {e}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              {dryRun && resultado.errors.length === 0 && (
                <Button
                  onClick={() => {
                    setDryRun(false)
                    setResultado(null)
                  }}
                >
                  Importar de verdade agora
                </Button>
              )}
              <Button variant="outline" onClick={onClose}>
                Fechar
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function ResultStat({
  label,
  value,
  color,
}: {
  label: string
  value: number
  color: string
}) {
  return (
    <div className="rounded-md bg-card p-2">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}
