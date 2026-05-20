import { ThemeToggle } from './theme-toggle'
import { UserMenu } from './user-menu'
import { Breadcrumb } from './breadcrumb'

interface TopbarProps {
  email: string
  name: string
  role: string
}

export function Topbar({ email, name, role }: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-12 items-center gap-3 border-b bg-card/80 backdrop-blur px-6">
      <div className="flex-1 min-w-0">
        <Breadcrumb />
      </div>
      <div className="flex items-center gap-1">
        <ThemeToggle />
        <UserMenu email={email} name={name} role={role} />
      </div>
    </header>
  )
}
