'use client'
import { useState } from 'react'
import { OsList } from '@/components/os-list'
import { OsCreatePanel } from '@/components/os-create-panel'

export default function OsPage() {
  const [showCreate, setShowCreate] = useState(false)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Ordens de serviço</h1>
        <p className="text-sm text-muted-foreground">Gerencie OS técnicas</p>
      </div>
      <div className={showCreate ? 'grid grid-cols-[1fr_400px] gap-4 items-start' : ''}>
        <OsList onNovaOs={() => setShowCreate(true)} />
        {showCreate && (
          <OsCreatePanel onCreated={() => setShowCreate(false)} />
        )}
      </div>
    </div>
  )
}
