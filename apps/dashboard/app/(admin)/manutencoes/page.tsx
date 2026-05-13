import { ManutencaoList } from '@/components/manutencao-list'

export default function ManutencoesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Manutenções</h1>
      </div>
      <ManutencaoList />
    </div>
  )
}
