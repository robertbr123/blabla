import { FormLead } from '@/components/form-lead'
import { PageHeader } from '@/components/noc/primitives'

export default function LeadNovoPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Novo Lead" />
      <FormLead />
    </div>
  )
}
