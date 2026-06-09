import AppLanding from './_components/AppLanding'

/**
 * Catch-all de qualquer path desconhecido (ex.: /faturas, /suporte,
 * /notificacoes vindos dos links de template WhatsApp quando o app
 * NAO esta instalado).
 *
 * Em vez do 404 padrao do Next, mostra a mesma landing da raiz
 * convidando a baixar o app. Com o app instalado, o SO intercepta a
 * URL via App Links antes do browser chegar aqui.
 *
 * Obs.: rotas reais (/, /privacidade) tem prioridade e nao caem aqui.
 * O HTTP status continua 404, o que e irrelevante pro App Link e pro
 * usuario final (ve a landing normalmente).
 */
export default function NotFound() {
  return <AppLanding />
}
