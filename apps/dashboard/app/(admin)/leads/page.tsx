import { LeadList } from '@/components/lead-list'
import { PageHeader } from '@/components/noc/primitives'

export default function LeadsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Leads"
        description="Gerencie os leads de entrada."
      />
      <LeadList />
    </div>
  )
}
