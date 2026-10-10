import { FormTecnico } from '@/components/form-tecnico'
import { PageHeader } from '@/components/noc/primitives'

export default function TecnicoNovoPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Novo Técnico" />
      <FormTecnico />
    </div>
  )
}
