'use client'
import { useRef } from 'react'
import { setAccessToken } from '@/lib/api/token'

export function TokenInitializer({ token }: { token: string }) {
  const didInit = useRef(false)
  if (!didInit.current) {
    didInit.current = true
    setAccessToken(token)
  }
  return null
}
