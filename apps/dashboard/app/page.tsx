import { redirect } from 'next/navigation'
import { getMeServer } from '@/lib/auth'

export default async function Home() {
  const me = await getMeServer()
  if (!me) redirect('/login')
  if (me.role === 'tecnico') redirect('/login')
  if (me.role === 'admin') redirect('/metricas')
  redirect('/conversas')
}
