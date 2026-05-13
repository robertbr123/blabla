import { ThemeToggle } from './theme-toggle'
import { UserMenu } from './user-menu'

interface TopbarProps {
  email: string
  name: string
  role: string
}

export function Topbar({ email, name, role }: TopbarProps) {
  return (
    <header className="flex h-14 items-center justify-end gap-2 border-b bg-card px-6">
      <ThemeToggle />
      <UserMenu email={email} name={name} role={role} />
    </header>
  )
}
