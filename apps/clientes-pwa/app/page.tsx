import AppLanding from './_components/AppLanding'

/**
 * Raiz do `clientes.ondeline.com.br` — mostra a landing de download.
 * A landing vive em `_components/AppLanding` e e reusada pelo not-found
 * (catch-all), pra que /faturas, /suporte, /notificacoes etc. tambem
 * caiam na landing quando o app nao esta instalado.
 */
export default function Page() {
  return <AppLanding />
}
