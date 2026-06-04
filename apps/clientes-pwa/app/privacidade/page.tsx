/**
 * Politica de Privacidade do app "Ondeline — cliente".
 *
 * URL publica: https://clientes.ondeline.com.br/privacidade
 * Usada como "Privacy Policy URL" obrigatoria no App Store Connect e
 * na Google Play Console.
 *
 * Server component puro (sem JS no client). Estilo casado com a landing
 * (app/page.tsx): navy + cinza claro, cartao branco arredondado.
 *
 * IMPORTANTE: revisar com o juridico antes de publicar. Os campos
 * marcados {{...}} (CNPJ, razao social, e-mail do encarregado) precisam
 * ser confirmados.
 */

import type { Metadata } from 'next'
import type { CSSProperties } from 'react'

export const metadata: Metadata = {
  title: 'Política de Privacidade — Ondeline',
  description:
    'Como o aplicativo Ondeline coleta, usa e protege seus dados pessoais.',
}

const NAVY = '#0B1F3A'
const BG = '#F4F6FA'
const TEXT = '#1A2540'
const MUTED = '#5B6884'

// Data da ultima revisao (atualizar manualmente a cada mudanca material).
const ATUALIZADO_EM = '04 de junho de 2026'

export default function PrivacidadePage() {
  return (
    <main
      style={{
        minHeight: '100vh',
        background: BG,
        color: TEXT,
        padding: '32px 20px 64px',
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        lineHeight: 1.6,
      }}
    >
      <article
        style={{
          background: 'white',
          borderRadius: 20,
          padding: '36px 28px',
          maxWidth: 720,
          margin: '0 auto',
          boxShadow: '0 20px 60px rgba(11, 31, 58, 0.08)',
        }}
      >
        <h1 style={{ color: NAVY, fontSize: 26, marginTop: 0 }}>
          Política de Privacidade
        </h1>
        <p style={{ color: MUTED, fontSize: 14, marginTop: -8 }}>
          Aplicativo <strong>Ondeline</strong> (cliente) · Última atualização:{' '}
          {ATUALIZADO_EM}
        </p>

        <p>
          Esta Política descreve como tratamos os seus dados pessoais quando
          você usa o aplicativo Ondeline para acompanhar seu plano de internet,
          faturas, chamados de suporte e atendimento. Tratamos os dados em
          conformidade com a Lei Geral de Proteção de Dados (Lei nº
          13.709/2018 — LGPD).
        </p>

        <h2 style={h2}>1. Quem é o controlador</h2>
        <p>
          O controlador dos dados é a Ondeline (ONDELINE TECNOLOGIA E SERVIÇOS
          DE INFORMÁTICA LTDA, CNPJ 49.840.386/0001-39), provedora de internet
          responsável pelo serviço contratado por você. Contato sobre
          privacidade:{' '}
          <a href="mailto:privacidade@ondeline.com.br">
            privacidade@ondeline.com.br
          </a>
          .
        </p>

        <h2 style={h2}>2. Dados que coletamos</h2>
        <ul>
          <li>
            <strong>Identificação e autenticação:</strong> CPF e senha de acesso
            ao app. A senha é armazenada de forma protegida; o CPF é usado para
            localizar seu cadastro.
          </li>
          <li>
            <strong>Biometria (Face ID / impressão digital):</strong> usada
            apenas para desbloquear o app no seu próprio aparelho. Esse dado{' '}
            <strong>não sai do dispositivo</strong> nem é enviado aos nossos
            servidores.
          </li>
          <li>
            <strong>Dados de cadastro e serviço:</strong> nome, endereço de
            instalação, data de nascimento, plano contratado, status da conexão,
            faturas, chamados de suporte e avaliações de atendimento (NPS).
          </li>
          <li>
            <strong>Identificador de notificação (token push):</strong> gerado
            pelo serviço de notificações para enviarmos avisos de fatura,
            atendimento e manutenção.
          </li>
          <li>
            <strong>Dados técnicos mínimos:</strong> informações necessárias ao
            funcionamento do app (ex.: versão e sistema do aparelho). O app{' '}
            <strong>não</strong> coleta sua localização e <strong>não</strong>{' '}
            usa rastreamento publicitário.
          </li>
        </ul>

        <h2 style={h2}>3. Para que usamos</h2>
        <ul>
          <li>Autenticar seu acesso e manter sua conta segura.</li>
          <li>
            Exibir seu plano, faturas (inclusive QR Pix) e histórico de
            atendimento.
          </li>
          <li>
            Enviar notificações sobre vencimento de faturas, andamento de
            chamados, manutenções na sua cidade e pesquisas de satisfação.
          </li>
          <li>Operar o programa de fidelidade e benefícios.</li>
          <li>Prestar suporte e cumprir obrigações legais e contratuais.</li>
        </ul>

        <h2 style={h2}>4. Compartilhamento</h2>
        <p>
          Não vendemos seus dados. Compartilhamos apenas o necessário com
          provedores que viabilizam o serviço, tais como:
        </p>
        <ul>
          <li>
            <strong>Google Firebase Cloud Messaging</strong> — entrega das
            notificações push.
          </li>
          <li>
            <strong>Sistema de gestão (ERP/SGP) da Ondeline</strong> — origem
            dos seus dados de plano, faturas e atendimento.
          </li>
          <li>
            <strong>WhatsApp</strong> — quando você opta por falar conosco por
            esse canal.
          </li>
          <li>
            Autoridades, quando exigido por lei ou ordem judicial.
          </li>
        </ul>

        <h2 style={h2}>5. Seus direitos (LGPD)</h2>
        <p>
          Você pode solicitar acesso, correção, portabilidade, anonimização ou
          exclusão dos seus dados, além de revogar consentimentos. O app oferece
          a opção de <strong>excluir a conta</strong> em Perfil. Para qualquer
          solicitação, fale com{' '}
          <a href="mailto:privacidade@ondeline.com.br">
            privacidade@ondeline.com.br
          </a>
          .
        </p>

        <h2 style={h2}>6. Retenção e segurança</h2>
        <p>
          Mantemos seus dados pelo tempo necessário à prestação do serviço e ao
          cumprimento de obrigações legais (por exemplo, fiscais). Adotamos
          medidas técnicas e organizacionais para proteger as informações, e
          toda a comunicação do app trafega de forma criptografada (HTTPS).
        </p>

        <h2 style={h2}>7. Crianças e adolescentes</h2>
        <p>
          O app destina-se ao titular do contrato. Não direcionamos o serviço a
          menores de 18 anos sem o consentimento dos responsáveis.
        </p>

        <h2 style={h2}>8. Alterações</h2>
        <p>
          Podemos atualizar esta Política. A data da última revisão sempre
          aparece no topo desta página.
        </p>

        <p style={{ color: MUTED, fontSize: 13, marginTop: 28 }}>
          Em caso de dúvidas, entre em contato pelo e-mail{' '}
          <a href="mailto:privacidade@ondeline.com.br">
            privacidade@ondeline.com.br
          </a>{' '}
          ou pelos canais de atendimento da Ondeline.
        </p>
      </article>
    </main>
  )
}

const h2: CSSProperties = {
  color: NAVY,
  fontSize: 18,
  marginTop: 28,
  marginBottom: 8,
}
