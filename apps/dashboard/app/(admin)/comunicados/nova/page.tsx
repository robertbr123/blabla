import { ComunicadoForm } from '@/components/comunicado-form'

export default function NovaCampanhaPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">Nova campanha</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Escolha o template, preencha as variáveis e segmente quem vai receber.
        </p>
      </div>
      <ComunicadoForm />
    </div>
  )
}
