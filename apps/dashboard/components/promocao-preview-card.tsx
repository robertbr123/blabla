'use client'
import { ArrowRight } from 'lucide-react'

interface Props {
  titulo: string
  subtitulo: string
  ctaLabel: string
  gradientFrom?: string | null
  gradientTo?: string | null
  imagemUrl?: string | null
  /** Nome do icone Material — se o app suportar mapping. Mostramos placeholder. */
  icon?: string | null
}

const DEFAULT_FROM = '#8B5CF6'
const DEFAULT_TO = '#5B6CFF'

export function PromocaoPreviewCard(props: Props) {
  const from = props.gradientFrom || DEFAULT_FROM
  const to = props.gradientTo || DEFAULT_TO
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">
        Pré-visualização (como aparece no app)
      </p>
      <div
        className="relative w-full overflow-hidden rounded-2xl p-5 shadow-lg"
        style={{
          background: `linear-gradient(135deg, ${from}, ${to})`,
          minHeight: 140,
        }}
      >
        {props.imagemUrl && (
          <img
            src={props.imagemUrl}
            alt=""
            className="absolute inset-0 h-full w-full object-cover opacity-30"
          />
        )}
        <div className="relative flex items-center gap-3">
          <div className="min-w-0 flex-1 text-white">
            <h3 className="line-clamp-2 text-base font-extrabold leading-tight tracking-tight">
              {props.titulo || 'Título da promoção'}
            </h3>
            <p className="mt-1 line-clamp-2 text-xs font-medium leading-snug text-white/80">
              {props.subtitulo || 'Subtítulo opcional descrevendo a oferta.'}
            </p>
            <span
              className="mt-3 inline-flex items-center gap-1 rounded-md border border-white/30 bg-white/20 px-3 py-1 text-[11px] font-bold text-white"
            >
              {props.ctaLabel || 'Saiba mais'}
              <ArrowRight className="h-3 w-3" />
            </span>
          </div>
          <div className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-white/20">
            {props.icon ? (
              <span className="font-mono text-[9px] text-white/90">
                {props.icon}
              </span>
            ) : (
              <div className="h-8 w-8 rounded-full bg-white/30" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
