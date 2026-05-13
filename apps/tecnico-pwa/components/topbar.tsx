'use client'
import { useRouter } from 'next/navigation'
import { LogOut, Wrench } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/auth'

export function Topbar({ name }: { name: string }) {
  const router = useRouter()
  async function handleLogout() {
    try {
      await logout()
    } finally {
      router.push('/login')
    }
  }
  return (
    <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b bg-card px-4">
      <div className="flex items-center gap-2">
        <Wrench className="h-5 w-5" />
        <span className="font-semibold">BlaBla Téc</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground truncate max-w-[120px]">{name}</span>
        <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Sair">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
