import { ComunicadoEditForm } from '@/components/comunicado-edit-form'

export default async function EditarComunicadoPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return (
    <div className="mx-auto max-w-2xl py-6">
      <h1 className="mb-6 text-2xl font-semibold">Editar comunicado</h1>
      <ComunicadoEditForm id={id} />
    </div>
  )
}
