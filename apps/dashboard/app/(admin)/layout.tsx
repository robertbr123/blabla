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
      <a href="#main-content" className="skip-to-main">
        Pular para o conteúdo
      </a>
      <TokenInitializer token={accessToken} />
      <NavSidebar role={me.role} />
      <div className="flex flex-1 flex-col">
        <Topbar email={me.email} name={me.name} role={me.role} />
        <main id="main-content" tabIndex={-1} className="flex-1 overflow-auto">
          <div className="mx-auto max-w-7xl px-6 py-6">{children}</div>
        </main>
      </div>
    </div>
  )
}
