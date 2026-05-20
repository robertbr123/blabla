'use client'
import { Suspense, useState } from 'react'
import Image from 'next/image'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter, useSearchParams } from 'next/navigation'
import { AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { login } from '@/lib/auth'

const schema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Informe a senha'),
})
type FormValues = z.infer<typeof schema>

function LoginForm() {
  const router = useRouter()
  const search = useSearchParams()
  const next = search.get('next') ?? '/conversas'
  const [error, setError] = useState<string | null>(null)
  const [showPwd, setShowPwd] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    setError(null)
    try {
      await login(values.email, values.password)
      router.push(next)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Erro ao fazer login'
      setError(msg)
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="space-y-1.5">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          autoFocus
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={errors.email ? 'email-error' : undefined}
          {...register('email')}
        />
        {errors.email && (
          <p id="email-error" className="text-xs text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="password">Senha</Label>
        <div className="relative">
          <Input
            id="password"
            type={showPwd ? 'text' : 'password'}
            autoComplete="current-password"
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={errors.password ? 'password-error' : undefined}
            className="pr-10"
            {...register('password')}
          />
          <button
            type="button"
            onClick={() => setShowPwd((v) => !v)}
            aria-label={showPwd ? 'Ocultar senha' : 'Mostrar senha'}
            tabIndex={-1}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {errors.password && (
          <p id="password-error" className="text-xs text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md bg-destructive/[0.10] px-3 py-2 text-sm text-destructive ring-1 ring-inset ring-destructive/30"
        >
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Entrando…
          </>
        ) : (
          'Entrar'
        )}
      </Button>
    </form>
  )
}

export default function LoginPage() {
  return (
    <main className="relative flex min-h-dvh items-center justify-center p-6 overflow-hidden bg-background">
      {/* Glow emerald sutil de fundo */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-60 dark:opacity-40"
        style={{
          background:
            'radial-gradient(60% 50% at 50% 0%, hsl(var(--primary) / 0.15), transparent 70%)',
        }}
      />

      <div className="relative w-full max-w-sm space-y-6">
        <div className="flex justify-center">
          <Image
            src="/branding/logo_horizontal_light.png"
            alt="BlaBla"
            width={160}
            height={42}
            priority
            className="h-10 w-auto dark:hidden"
          />
          <Image
            src="/branding/logo_horizontal_dark.png"
            alt="BlaBla"
            width={160}
            height={42}
            priority
            className="hidden h-10 w-auto dark:block"
          />
        </div>

        <Card className="shadow-lg">
          <CardContent className="space-y-5 p-6">
            <div className="space-y-1 text-center">
              <h1 className="text-lg font-semibold">Acesse seu painel</h1>
              <p className="text-xs text-muted-foreground">
                Entre com seu email e senha pra continuar.
              </p>
            </div>
            <Suspense fallback={null}>
              <LoginForm />
            </Suspense>
          </CardContent>
        </Card>

        <p className="text-center text-[11px] text-muted-foreground">
          Acesso restrito · administradores e atendentes
        </p>
      </div>
    </main>
  )
}
