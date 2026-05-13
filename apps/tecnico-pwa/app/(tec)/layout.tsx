import { redirect } from 'next/navigation'
import { Topbar } from '@/components/topbar'
import { getMeServer } from '@/lib/auth'

export default async function TecLayout({ children }: { children: React.ReactNode }) {
  const me = await getMeServer()
  if (!me) redirect('/login')
  if (me.role !== 'tecnico') redirect('/login')
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Topbar name={me.name || me.email} />
      <main className="flex-1 p-4">{children}</main>
    </div>
  )
}
