'use client'

import { useEffect, useState } from 'react'

/**
 * Abre a loja (Play/App Store) automaticamente apos `delayMs` se o
 * usuario nao tocar num botao antes. Renderizado so no mobile (ios/
 * android) pelo `AppLanding`.
 *
 * Guard de sessao (`sessionStorage`): redireciona uma unica vez por
 * aba, pra que o botao "voltar" da loja nao caia num loop
 * landing -> loja -> landing -> loja.
 *
 * Mostra um aviso discreto com contagem regressiva pra deixar claro
 * o que vai acontecer.
 */
const REDIRECT_FLAG = 'ondeline:auto-redirect-done'

export default function AutoRedirect({
  url,
  delayMs = 3000,
}: {
  url: string
  delayMs?: number
}) {
  const [seconds, setSeconds] = useState(Math.ceil(delayMs / 1000))

  useEffect(() => {
    if (sessionStorage.getItem(REDIRECT_FLAG)) {
      setSeconds(0)
      return
    }

    const tick = setInterval(() => {
      setSeconds((s) => (s > 0 ? s - 1 : 0))
    }, 1000)

    const timer = setTimeout(() => {
      sessionStorage.setItem(REDIRECT_FLAG, '1')
      window.location.href = url
    }, delayMs)

    return () => {
      clearInterval(tick)
      clearTimeout(timer)
    }
  }, [url, delayMs])

  if (seconds <= 0) return null

  return (
    <p style={{ marginTop: 16, fontSize: 13, color: '#5B6884' }}>
      Abrindo a loja automaticamente em {seconds}s…
    </p>
  )
}
