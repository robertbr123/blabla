import { redirect } from 'next/navigation'
import { NavSidebar } from '@/components/nav-sidebar'
import { Topbar } from '@/components/topbar'
import { TokenInitializer } from '@/components/token-initializer'
import { getMeServer } from '@/lib/auth'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const result = await getMeServer()
  if (!result) {
    redirect('/login')
  }
  const { me, accessToken } = result
  if (me.role === 'tecnico') {
    redirect('/login') // técnicos usam o PWA, não o dashboard
  }
  return (
    <div className="flex min-h-screen">
      <TokenInitializer token={accessToken} />
      <NavSidebar role={me.role} />
      <div className="flex flex-1 flex-col">
        <Topbar email={me.email} name={me.name} role={me.role} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
