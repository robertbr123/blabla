'use client'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { PageHeader } from '@/components/noc/primitives'
import { OsList } from '@/components/os-list'
import { OsCreatePanel } from '@/components/os-create-panel'
import { Button } from '@/components/ui/button'

export default function OsPage() {
  const [showCreate, setShowCreate] = useState(false)

  return (
    <div className="space-y-4">
      <PageHeader
        title="Ordens de serviço"
        description="Fila de atendimento técnico em campo"
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" /> Nova OS
          </Button>
        }
      />
      <div
        className={
          showCreate
            ? 'grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_400px]'
            : undefined
        }
      >
        <OsList onNovaOs={() => setShowCreate(true)} />
        {showCreate && (
          <OsCreatePanel
            onCreated={() => setShowCreate(false)}
            onClose={() => setShowCreate(false)}
          />
        )}
      </div>
    </div>
  )
}
