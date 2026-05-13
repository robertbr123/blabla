import { FormOsCreate } from '@/components/form-os-create'

export default function NovaOsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Nova OS</h1>
      </div>
      <FormOsCreate />
    </div>
  )
}
