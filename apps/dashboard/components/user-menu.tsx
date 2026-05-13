'use client'
import { useRouter } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/auth'

interface UserMenuProps {
  email: string
  name: string
  role: string
}

export function UserMenu({ email, name, role }: UserMenuProps) {
  const router = useRouter()
  async function handleLogout() {
    try {
      await logout()
    } finally {
      router.push('/login')
    }
  }
  return (
    <div className="flex items-center gap-3">
      <div className="text-right text-sm">
        <div className="font-medium leading-none">{name || email}</div>
        <div className="text-xs text-muted-foreground capitalize">{role}</div>
      </div>
      <Button variant="ghost" size="icon" aria-label="Sair" onClick={handleLogout}>
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  )
}
