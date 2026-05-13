import { FormTecnico } from '@/components/form-tecnico'

export default function TecnicoNovoPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Novo Técnico</h1>
      </div>
      <FormTecnico />
    </div>
  )
}
