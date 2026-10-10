'use client'
import { useRouter } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/auth'
import { Avatar } from './noc/primitives'

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
    <div className="flex items-center gap-2.5 pl-1">
      <Avatar name={name || email} size="sm" />
      <div className="hidden text-left leading-tight lg:block">
        <div className="max-w-[160px] truncate text-[13px] font-medium">{name || email}</div>
        <div className="text-[11px] capitalize text-muted-foreground">{role}</div>
      </div>
      <Button variant="ghost" size="icon" aria-label="Sair" onClick={handleLogout}>
        <LogOut className="h-4 w-4" />
      </Button>
    </div>
  )
}
