import { FormManutencao } from '@/components/form-manutencao'

export default function NovaManutencaoPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Nova manutenção</h1>
      </div>
      <FormManutencao />
    </div>
  )
}
