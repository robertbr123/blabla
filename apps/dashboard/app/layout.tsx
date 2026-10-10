import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Providers } from './providers'
import { Toaster } from 'sonner'

export const metadata: Metadata = {
  title: 'BlaBla',
  description: 'Painel administrativo BlaBla',
}

// `resizes-content`: no Android o teclado virtual encolhe o layout (e o `dvh`),
// então o campo de resposta do chat fica colado acima do teclado em vez de
// ficar escondido atrás dele. (O iOS ignora e mantém o comportamento padrão.)
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  interactiveWidget: 'resizes-content',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="font-sans">
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  )
}
