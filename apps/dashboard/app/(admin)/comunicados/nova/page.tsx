import { ComunicadoForm } from '@/components/comunicado-form'
import { PageHeader } from '@/components/noc/primitives'

export default function NovaCampanhaPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title="Nova campanha"
        description="Escolha o template, preencha as variáveis e segmente quem vai receber."
      />
      <ComunicadoForm />
    </div>
  )
}
