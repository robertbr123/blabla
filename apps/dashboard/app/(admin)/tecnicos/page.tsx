import { TecnicoList } from '@/components/tecnico-list'

export default function TecnicosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Técnicos</h1>
        <p className="mt-1 text-sm text-muted-foreground">Gerencie os técnicos de campo.</p>
      </div>
      <TecnicoList />
    </div>
  )
}
