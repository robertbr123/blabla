import { LeadList } from '@/components/lead-list'

export default function LeadsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Leads</h1>
        <p className="mt-1 text-sm text-muted-foreground">Gerencie os leads de entrada.</p>
      </div>
      <LeadList />
    </div>
  )
}
