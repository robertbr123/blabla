import { FormOsCreate } from '@/components/form-os-create'
import { PageHeader } from '@/components/noc/primitives'

export default function NovaOsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Nova OS" />
      <FormOsCreate />
    </div>
  )
}
