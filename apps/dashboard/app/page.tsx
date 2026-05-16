import { redirect } from 'next/navigation'
import { getMeServer } from '@/lib/auth'

export default async function Home() {
  const result = await getMeServer()
  if (!result) redirect('/login')
  if (result.me.role === 'tecnico') redirect('/login')
  if (result.me.role === 'admin') redirect('/metricas')
  redirect('/conversas')
}
