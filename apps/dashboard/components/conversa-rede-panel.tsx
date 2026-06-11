'use client'
import { Loader2, RotateCw, Wifi, WifiOff } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useRedeDiagnostico,
  useReiniciarOnu,
  useRedeStatusConversa,
  useTrocarSenhaConversa,
} from '@/lib/api/queries'
import type { RedeDiagnostico } from '@/lib/api/types'

/** Cor do RX power (GPON, dBm): verde -8..-25, amarelo -25..-27, vermelho fora. */
export function corRx(rx: number | null | undefined): string {
  if (rx == null) return 'text-muted-foreground'
  if (rx > -8 || rx < -27) return 'text-red-500'
  if (rx < -25) return 'text-amber-500'
  return 'text-green-500'
}

export function fmtUptime(s: number | null | undefined): string {
  if (s == null) return '—'
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}min`
  return `${m}min`
}

/** Resumo amigável pra colar na conversa. */
export function resumoDiagnostico(d: RedeDiagnostico): string {
  if (!d.encontrada) return 'Não localizei o equipamento deste cliente na rede.'
  const partes: string[] = []
  if (d.sinal?.rx_power != null) partes.push(`sinal ${d.sinal.rx_power} dBm`)
  if (d.sinal?.conexao_pppoe) partes.push(`conexão ${d.sinal.conexao_pppoe}`)
  if (d.sinal?.uptime_s != null) partes.push(`estável há ${fmtUptime(d.sinal.uptime_s)}`)
  partes.push(`${d.aparelhos.length} aparelho(s) conectado(s)`)
  return `Diagnóstico da sua rede: ${partes.join(', ')}.`
}

interface Props {
  conversaId: string
  temCliente: boolean
  onColarDiagnostico: (texto: string) => void
}

export function ConversaRedePanel({ conversaId, temCliente, onColarDiagnostico }: Props) {
  const diag = useRedeDiagnostico(conversaId, temCliente)
  const trocar = useTrocarSenhaConversa(conversaId)
  const reboot = useReiniciarOnu(conversaId)
  const [senha, setSenha] = useState('')

  if (!temCliente) {
    return (
      <p className="text-sm text-muted-foreground">
        Vincule o cliente à conversa para ver e gerenciar a rede.
      </p>
    )
  }
  if (diag.isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
  }
  if (diag.isError || !diag.data) {
    return <p className="text-sm text-destructive">Não foi possível carregar a rede.</p>
  }
  const d = diag.data
  if (!d.encontrada) {
    return (
      <p className="text-sm text-muted-foreground">
        Cliente sem equipamento gerenciável na rede.
      </p>
    )
  }

  async function confirmarEReboot() {
    if (!window.confirm('A internet do cliente vai reiniciar e volta em ~2min. Continuar?')) return
    const r = await reboot.mutateAsync()
    if (r) window.alert(r.aviso)
  }

  async function confirmarETrocar() {
    if (senha.length < 8 || senha.length > 63) {
      window.alert('A senha deve ter de 8 a 63 caracteres.')
      return
    }
    if (!window.confirm('A internet do cliente pode reiniciar (~2min) ao trocar a senha. Continuar?')) return
    const r = await trocar.mutateAsync(senha)
    if (r) {
      window.alert(r.aviso)
      setSenha('')
    }
  }

  return (
    <div className="space-y-4 text-sm">
      <div>
        <p className="font-semibold">Sinal da fibra</p>
        {d.sinal == null ? (
          <p className="text-muted-foreground">
            Ainda não disponível — atualize em ~5min.
          </p>
        ) : (
          <div className="space-y-0.5">
            <p>
              <span className={corRx(d.sinal.rx_power)}>● </span>
              RX: {d.sinal.rx_power ?? '—'} dBm · TX: {d.sinal.tx_power ?? '—'} dBm
            </p>
            <p>
              GPON: {d.sinal.status_gpon ?? '—'} · PPPoE: {d.sinal.conexao_pppoe ?? '—'}
            </p>
            {d.sinal.ip_externo && <p>IP: {d.sinal.ip_externo}</p>}
            <p>Uptime: {fmtUptime(d.sinal.uptime_s)}</p>
          </div>
        )}
        {d.pppoe_login && <p>Login PPPoE: {d.pppoe_login}</p>}
      </div>

      <div>
        <p className="font-semibold">Aparelhos conectados ({d.aparelhos.length})</p>
        {d.aparelhos.length === 0 ? (
          <p className="text-muted-foreground">Nenhum aparelho no momento.</p>
        ) : (
          <ul className="space-y-0.5">
            {d.aparelhos.map((a) => (
              <li key={a.mac} className="font-mono text-xs">
                {a.nome || a.ip} · {a.ip} · {a.mac}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-2 border-t pt-3">
        <Input
          placeholder="Nova senha do WiFi (8–63)"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={confirmarETrocar} disabled={trocar.isPending}>
            {trocar.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Trocar senha'}
          </Button>
          <Button size="sm" variant="outline" onClick={confirmarEReboot} disabled={reboot.isPending}>
            <RotateCw className="mr-1 h-4 w-4" /> Reiniciar ONU
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onColarDiagnostico(resumoDiagnostico(d))}>
            Colar diagnóstico na resposta
          </Button>
        </div>
      </div>
    </div>
  )
}

/** Selo de saúde pro header da conversa. */
export function RedeBadge({ conversaId, temCliente }: { conversaId: string; temCliente: boolean }) {
  const st = useRedeStatusConversa(conversaId, temCliente)
  if (!temCliente || !st.data?.encontrada) return null
  return st.data.online ? (
    <span className="inline-flex items-center gap-1 text-xs text-green-600">
      <Wifi className="h-3 w-3" /> online
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <WifiOff className="h-3 w-3" /> offline
    </span>
  )
}
