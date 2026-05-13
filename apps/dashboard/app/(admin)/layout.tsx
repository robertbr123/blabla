import { redirect } from 'next/navigation'
import { NavSidebar } from '@/components/nav-sidebar'
import { Topbar } from '@/components/topbar'
import { getMeServer } from '@/lib/auth'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const me = await getMeServer()
  if (!me) {
    redirect('/login')
  }
  if (me.role === 'tecnico') {
    redirect('/login') // técnicos usam o PWA, não o dashboard
  }
  return (
    <div className="flex min-h-screen">
      <NavSidebar role={me.role} />
      <div className="flex flex-1 flex-col">
        <Topbar email={me.email} name={me.name} role={me.role} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
