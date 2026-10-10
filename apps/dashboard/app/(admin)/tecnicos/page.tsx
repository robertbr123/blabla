import { TecnicoList } from '@/components/tecnico-list'
import { PageHeader } from '@/components/noc/primitives'

export default function TecnicosPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Técnicos"
        description="Gerencie os técnicos de campo."
      />
      <TecnicoList />
    </div>
  )
}
