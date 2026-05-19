'use client'
/**
 * Respostas rápidas pra atendente humano. Digitando `/` no início abre menu
 * com snippets pré-definidos. Usa setas pra navegar e Enter pra inserir.
 *
 * V1 com snippets fixos. Próxima iteração: persistir em config table pra
 * admin editar via dashboard.
 */
import { useEffect, useRef, useState } from 'react'

export interface QuickReply {
  slug: string  // "/saudacao", "/aguarde"
  label: string // texto curto exibido no menu
  body: string  // texto que será inserido
}

export const QUICK_REPLIES: QuickReply[] = [
  {
    slug: '/saudacao',
    label: 'Saudação inicial',
    body: 'Olá! Aqui é o suporte da Ondeline. Em que posso te ajudar?',
  },
  {
    slug: '/aguarde',
    label: 'Pedir pra aguardar',
    body: 'Só um momento, vou verificar isso pra você. 🙏',
  },
  {
    slug: '/verificando',
    label: 'Verificando sistema',
    body: 'Estou verificando seu cadastro no sistema, aguarde só um instante. 🔎',
  },
  {
    slug: '/agendar',
    label: 'Agendar visita técnica',
    body: 'Vou agendar uma visita técnica pra você. Que dia/horário fica melhor?',
  },
  {
    slug: '/tecnico-caminho',
    label: 'Técnico a caminho',
    body: 'O técnico já está a caminho. 🚗 Em breve ele chega aí!',
  },
  {
    slug: '/pagamento',
    label: 'Confirmação de pagamento',
    body: 'Confirmei seu pagamento aqui, está tudo certo! Obrigado. ✅',
  },
  {
    slug: '/desculpa',
    label: 'Pedido de desculpas',
    body: 'Peço desculpas pelo inconveniente. Vou resolver isso o mais rápido possível!',
  },
  {
    slug: '/agradecimento',
    label: 'Agradecimento',
    body: 'Muito obrigado pelo contato! Qualquer coisa, é só chamar. 😊',
  },
  {
    slug: '/encerrar',
    label: 'Encerrar atendimento',
    body: 'Resolvido por aqui? Se ficou tudo certo, vou encerrar nosso atendimento. Qualquer dúvida, é só chamar! 👋',
  },
  {
    slug: '/horario',
    label: 'Fora de horário',
    body: 'Nosso atendimento é de segunda a sexta, das 8h às 18h. Vou retornar assim que possível!',
  },
]

interface Props {
  text: string
  onSelect: (body: string) => void
  /** Posição vertical do menu — 'above' (sobre o input) ou 'below'. Default 'above'. */
  position?: 'above' | 'below'
}

export function QuickRepliesMenu({ text, onSelect, position = 'above' }: Props) {
  const [highlight, setHighlight] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)

  // Filtra pelo query depois do /
  const trimmed = text.trim()
  const open = trimmed.startsWith('/') && !trimmed.includes(' ')
  const query = trimmed.slice(1).toLowerCase()
  const matches = open
    ? QUICK_REPLIES.filter(
        (q) =>
          query === '' ||
          q.slug.toLowerCase().includes(query) ||
          q.label.toLowerCase().includes(query),
      )
    : []

  useEffect(() => {
    if (matches.length === 0) setHighlight(0)
    else if (highlight >= matches.length) setHighlight(0)
  }, [matches.length, highlight])

  if (!open || matches.length === 0) return null

  return (
    <div
      ref={listRef}
      className={`absolute left-0 right-0 z-10 max-h-60 overflow-y-auto rounded-md border bg-card shadow-lg ${
        position === 'above' ? 'bottom-full mb-2' : 'top-full mt-2'
      }`}
      role="listbox"
    >
      {matches.map((q, idx) => (
        <button
          key={q.slug}
          type="button"
          onClick={() => onSelect(q.body)}
          onMouseEnter={() => setHighlight(idx)}
          className={`flex w-full flex-col items-start gap-0.5 border-b px-3 py-2 text-left text-sm last:border-b-0 ${
            idx === highlight ? 'bg-muted' : 'hover:bg-muted/50'
          }`}
        >
          <div className="flex w-full items-center gap-2">
            <code className="font-mono text-xs text-primary">{q.slug}</code>
            <span className="text-xs font-medium">{q.label}</span>
          </div>
          <span className="line-clamp-1 text-xs text-muted-foreground">{q.body}</span>
        </button>
      ))}
      <div className="border-t bg-muted/30 px-3 py-1.5 text-[10px] text-muted-foreground">
        ↑/↓ navegar · Enter inserir · Esc fechar
      </div>
    </div>
  )
}

/** Hook que processa eventos de teclado pra navegação no menu. */
export function useQuickRepliesKeyHandler(
  text: string,
  setText: (v: string) => void,
): {
  isMenuOpen: boolean
  matches: QuickReply[]
  highlight: number
  onKeyDown: (e: React.KeyboardEvent) => boolean // retorna true se consumiu
} {
  const [highlight, setHighlight] = useState(0)

  const trimmed = text.trim()
  const open = trimmed.startsWith('/') && !trimmed.includes(' ')
  const query = trimmed.slice(1).toLowerCase()
  const matches = open
    ? QUICK_REPLIES.filter(
        (q) =>
          query === '' ||
          q.slug.toLowerCase().includes(query) ||
          q.label.toLowerCase().includes(query),
      )
    : []

  function onKeyDown(e: React.KeyboardEvent): boolean {
    if (!open || matches.length === 0) return false
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight((h) => (h + 1) % matches.length)
      return true
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => (h - 1 + matches.length) % matches.length)
      return true
    }
    if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault()
      const choice = matches[Math.min(highlight, matches.length - 1)]
      if (choice) setText(choice.body)
      return true
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      setText('')
      return true
    }
    return false
  }

  return { isMenuOpen: open && matches.length > 0, matches, highlight, onKeyDown }
}
