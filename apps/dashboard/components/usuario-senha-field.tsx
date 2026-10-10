'use client'
import { useState } from 'react'
import type { UseFormRegisterReturn } from 'react-hook-form'
import { Check, Copy, Eye, EyeOff, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export const SENHA_MIN = 8

// Sem caracteres ambiguos (0/O, 1/l/I) — a senha costuma ser ditada ou digitada.
const MINUSCULAS = 'abcdefghijkmnpqrstuvwxyz'
const MAIUSCULAS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
const DIGITOS = '23456789'
const ALFABETO = MINUSCULAS + MAIUSCULAS + DIGITOS

function sortear(alfabeto: string, n: number): string {
  // Rejeicao pra nao enviesar o modulo.
  const limite = 256 - (256 % alfabeto.length)
  let out = ''
  while (out.length < n) {
    const bytes = new Uint8Array(n * 2)
    crypto.getRandomValues(bytes)
    bytes.forEach((b) => {
      if (b < limite && out.length < n) out += alfabeto.charAt(b % alfabeto.length)
    })
  }
  return out
}

/** Senha aleatoria de 12 caracteres com minuscula, maiuscula e digito. */
export function gerarSenha(tamanho = 12): string {
  for (;;) {
    const s = sortear(ALFABETO, tamanho)
    if (/[a-z]/.test(s) && /[A-Z]/.test(s) && /[0-9]/.test(s)) return s
  }
}

export function UsuarioSenhaField({
  id,
  label,
  registration,
  error,
  show,
  onShowChange,
  onGerar,
  getValue,
  hint,
  autoFocus,
}: {
  id: string
  label: string
  registration: UseFormRegisterReturn
  error?: string
  show: boolean
  onShowChange: (show: boolean) => void
  /** Preenche o campo com uma senha aleatoria (o pai tambem revela). */
  onGerar: () => void
  /** Valor atual, lido so na hora de copiar. */
  getValue: () => string
  hint?: React.ReactNode
  autoFocus?: boolean
}) {
  const [copiada, setCopiada] = useState(false)

  async function copiar() {
    const v = getValue()
    if (!v) return
    try {
      await navigator.clipboard.writeText(v)
      setCopiada(true)
      setTimeout(() => setCopiada(false), 2000)
    } catch {
      // Sem permissao de clipboard: revela pra copiar na mao.
      onShowChange(true)
    }
  }

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <Input
            id={id}
            type={show ? 'text' : 'password'}
            autoComplete="new-password"
            autoCapitalize="none"
            spellCheck={false}
            autoFocus={autoFocus}
            aria-invalid={error ? true : undefined}
            aria-describedby={`${id}-ajuda`}
            className={show ? 'num pr-[4.5rem]' : 'pr-[4.5rem]'}
            {...registration}
          />
          <div className="absolute right-1 top-1/2 flex -translate-y-1/2 items-center">
            <button
              type="button"
              onClick={() => void copiar()}
              title={copiada ? 'Senha copiada' : 'Copiar senha'}
              aria-label={copiada ? 'Senha copiada' : 'Copiar senha'}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {copiada ? (
                <Check aria-hidden className="h-4 w-4 text-success" />
              ) : (
                <Copy aria-hidden className="h-4 w-4" />
              )}
            </button>
            <button
              type="button"
              onClick={() => onShowChange(!show)}
              title={show ? 'Ocultar senha' : 'Mostrar senha'}
              aria-label={show ? 'Ocultar senha' : 'Mostrar senha'}
              aria-pressed={show}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {show ? (
                <EyeOff aria-hidden className="h-4 w-4" />
              ) : (
                <Eye aria-hidden className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
        <Button type="button" variant="outline" onClick={onGerar} className="shrink-0">
          <RefreshCw aria-hidden /> Gerar senha
        </Button>
      </div>
      <div id={`${id}-ajuda`} className="space-y-1">
        {error && <p className="text-xs text-destructive">{error}</p>}
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <span role="status" className="sr-only">
        {copiada ? 'Senha copiada' : ''}
      </span>
    </div>
  )
}
