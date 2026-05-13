import { OsList } from '@/components/os-list'

export default function OsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ordens de serviço</h1>
        <p className="text-sm text-muted-foreground">
          Gerencie OS técnicas
        </p>
      </div>
      <OsList />
    </div>
  )
}
