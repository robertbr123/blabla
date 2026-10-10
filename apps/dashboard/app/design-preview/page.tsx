'use client'
/**
 * Vitrine do design system NOC — dados ficticios, sem chamada de API.
 * Serve pra conferir tokens e primitivas nos dois temas sem precisar logar.
 * Fonte da verdade: design-system/blabla-dashboard/MASTER.md
 */
import { useState } from 'react'
import { CheckCircle2, Clock, Headphones, MessageSquare, Star, Wrench } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ConversaStatusPill } from '@/components/conversa-status-pill'
import { OsStatusPill } from '@/components/os-status-pill'
import { ThemeToggle } from '@/components/theme-toggle'
import {
  Avatar,
  FilterTabs,
  PageHeader,
  Panel,
  PanelBody,
  PanelHeader,
  StatTile,
  StatusChip,
  StatusDot,
} from '@/components/noc/primitives'
import { Sparkline } from '@/components/noc/sparkline'

const SURFACES = [
  { name: 'background', cls: 'bg-background' },
  { name: 'sidebar', cls: 'bg-sidebar' },
  { name: 'card', cls: 'bg-card' },
  { name: 'elevated', cls: 'bg-elevated' },
  { name: 'muted', cls: 'bg-muted' },
  { name: 'secondary', cls: 'bg-secondary' },
]

const STATUS = [
  { name: 'success', cls: 'bg-success' },
  { name: 'warning', cls: 'bg-warning' },
  { name: 'destructive', cls: 'bg-destructive' },
  { name: 'info', cls: 'bg-info' },
  { name: 'primary', cls: 'bg-primary' },
]

const CHART = [
  { name: 'chart-1', cls: 'bg-chart-1' },
  { name: 'chart-2', cls: 'bg-chart-2' },
  { name: 'chart-3', cls: 'bg-chart-3' },
]

const FILA = [
  { nome: 'Maria Souza', fone: '(97) 9 8401-2233', espera: '18 min', estourado: true },
  { nome: 'João Pereira', fone: '(97) 9 8455-9012', espera: '9 min', estourado: false },
  { nome: 'Ana Lima', fone: '(97) 9 8420-7781', espera: '2 min', estourado: false },
]

type Filtro = 'todas' | 'aguardando' | 'humano' | 'bot'

function Swatches({ title, items }: { title: string; items: { name: string; cls: string }[] }) {
  return (
    <div>
      <div className="eyebrow mb-2">{title}</div>
      <div className="flex flex-wrap gap-3">
        {items.map((s) => (
          <div key={s.name} className="w-24">
            <div className={`h-12 rounded-md border ${s.cls}`} />
            <div className="num mt-1 text-[11px] text-muted-foreground">{s.name}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function DesignPreviewPage() {
  const [filtro, setFiltro] = useState<Filtro>('todas')
  return (
    <main className="noc-canvas min-h-dvh bg-background">
      <div className="mx-auto max-w-[1200px] space-y-6 px-5 py-6">
        <PageHeader
          title="Design system — NOC"
          description="Tokens e primitivas do painel. Dados fictícios."
          actions={<ThemeToggle />}
        />

        <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card px-4 py-2.5">
          <StatusDot tone="success" pulse />
          <span className="text-sm font-medium">Todos os sistemas operacionais</span>
          <div className="ml-auto flex flex-wrap gap-2">
            <StatusChip tone="success" label="WhatsApp" value="Conectado" />
            <StatusChip tone="success" label="Banco" value="OK" />
            <StatusChip tone="warning" label="Worker" value="Lento" pulse />
            <StatusChip tone="destructive" label="Fila" value="Falha" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Fila aguardando" value={3} icon={Clock} tone="destructive" alert hint="1 com SLA estourado" />
          <StatTile label="Em atendimento" value={7} icon={Headphones} tone="info" hint="Com atendente humano" />
          <StatTile label="OS abertas" value={12} icon={Wrench} tone="warning" alert hint="2 sem técnico" />
          <StatTile label="Mensagens 24h" value="1.284" icon={MessageSquare} hint="Últimas 24 horas">
            <Sparkline
              values={[820, 910, 760, 1040, 1190, 980, 1284]}
              color="var(--chart-1)"
              label="Mensagens por dia, exemplo"
            />
          </StatTile>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Panel>
            <PanelHeader title="Fila de atendimento" icon={Clock} meta={FILA.length} />
            <ul>
              {FILA.map((f) => (
                <li
                  key={f.nome}
                  className={`flex items-center gap-3 border-b border-border/70 px-4 py-2.5 last:border-b-0 ${f.estourado ? 'animate-breach' : ''}`}
                >
                  <Avatar name={f.nome} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{f.nome}</div>
                    <div className="num text-xs text-muted-foreground">{f.fone}</div>
                  </div>
                  <span className={`num text-sm font-semibold ${f.estourado ? 'text-destructive' : ''}`}>
                    {f.espera}
                  </span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel>
            <PanelHeader title="Componentes" icon={Star} />
            <PanelBody className="space-y-4">
              <FilterTabs<Filtro>
                ariaLabel="Filtro de exemplo"
                value={filtro}
                onChange={setFiltro}
                tabs={[
                  { value: 'todas', label: 'Todas' },
                  { value: 'aguardando', label: 'Aguardando', count: 3, tone: 'warning' },
                  { value: 'humano', label: 'Humano', count: 7, tone: 'info' },
                  { value: 'bot', label: 'Bot', tone: 'muted' },
                ]}
              />
              <div className="flex flex-wrap gap-2">
                <ConversaStatusPill status="aguardando" size="sm" />
                <ConversaStatusPill status="humano" size="sm" />
                <ConversaStatusPill status="bot" size="sm" />
                <ConversaStatusPill status="encerrada" size="sm" />
              </div>
              <div className="flex flex-wrap gap-2">
                <OsStatusPill status="pendente" size="sm" />
                <OsStatusPill status="em_andamento" size="sm" />
                <OsStatusPill status="concluida" size="sm" />
                <OsStatusPill status="cancelada" size="sm" />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm">
                  <CheckCircle2 /> Primário
                </Button>
                <Button size="sm" variant="outline">
                  Contorno
                </Button>
                <Button size="sm" variant="secondary">
                  Secundário
                </Button>
                <Button size="sm" variant="ghost">
                  Fantasma
                </Button>
                <Button size="sm" variant="destructive">
                  Destrutivo
                </Button>
              </div>
              <Input placeholder="Buscar por nome ou WhatsApp…" className="max-w-xs" />
            </PanelBody>
          </Panel>
        </div>

        <Panel>
          <PanelHeader title="Tabela" />
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Cliente</th>
                  <th>Status</th>
                  <th>Técnico</th>
                  <th>Aberta há</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="num font-medium">OS-20261009-014</td>
                  <td>Maria Souza</td>
                  <td><OsStatusPill status="em_andamento" size="sm" /></td>
                  <td>Carlos Dias</td>
                  <td className="num text-muted-foreground">3 h</td>
                </tr>
                <tr>
                  <td className="num font-medium">OS-20261009-013</td>
                  <td>João Pereira</td>
                  <td><OsStatusPill status="pendente" size="sm" /></td>
                  <td className="text-warning">Sem técnico</td>
                  <td className="num text-muted-foreground">5 h</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Cores" />
          <PanelBody className="space-y-5">
            <Swatches title="Superfícies" items={SURFACES} />
            <Swatches title="Status (reservadas para estado)" items={STATUS} />
            <Swatches title="Séries de gráfico" items={CHART} />
          </PanelBody>
        </Panel>
      </div>
    </main>
  )
}
