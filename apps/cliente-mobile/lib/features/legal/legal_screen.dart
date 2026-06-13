import 'package:flutter/material.dart';

import '../../core/branding/brand_tokens.dart';
import '../../core/ui/glass_app_bar.dart';

/// Tela generica que renderiza um documento legal (termos / privacidade).
class LegalScreen extends StatelessWidget {
  const LegalScreen({super.key, required this.title, required this.body});
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final topPad = MediaQuery.paddingOf(context).top +
        kToolbarHeight +
        BrandTokens.spaceMd;
    return Scaffold(
      appBar: GlassAppBar(title: title),
      extendBodyBehindAppBar: true,
      body: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            BrandTokens.spaceLg,
            topPad,
            BrandTokens.spaceLg,
            BrandTokens.spaceLg,
          ),
          child: Text(
            body,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.45),
          ),
        ),
      ),
    );
  }
}

const termosUsoBody = '''Termos de Uso — Ondeline Telecom

Ultima atualizacao: 21 de maio de 2026.

1. Aceitacao
Ao usar o app Ondeline, voce concorda com estes Termos e com a Politica de Privacidade.

2. Cadastro
O acesso ao app exige cadastro com CPF, com validacao por codigo enviado no WhatsApp do numero cadastrado em seu contrato com a Ondeline.

3. Uso permitido
O app destina-se a clientes ativos da Ondeline Telecom para consulta de plano, 2a via de faturas, abertura de chamados e contato com suporte. E vedado o uso para qualquer finalidade ilicita, abusiva ou que viole os Termos.

4. Limitacoes do servico
A Ondeline empenha esforcos para manter o app disponivel, mas nao garante disponibilidade ininterrupta. Problemas podem ocorrer por manutencao, instabilidade de rede, falhas de terceiros ou caso fortuito.

5. Conta
Voce e responsavel pela manutencao da seguranca de sua senha e dos dispositivos em que o app esta instalado. Em caso de perda do dispositivo, recomendamos trocar a senha imediatamente.

6. Encerramento
A Ondeline pode encerrar o acesso ao app em caso de violacao destes Termos ou encerramento do contrato.

7. Atualizacoes
Estes Termos podem ser atualizados. Manteremos no app a versao vigente.

8. Foro
Fica eleito o foro da comarca de Manaus/AM para dirimir quaisquer controversias.

Contato: contato@ondelinetelecom.com.br''';

const politicaPrivacidadeBody = '''Politica de Privacidade — Ondeline Telecom

Ultima atualizacao: 21 de maio de 2026.

1. Dados que coletamos
- Identificacao: CPF, nome e telefone (do seu contrato).
- Contato: email (opcional, fornecido por voce).
- Tecnicos: identificador do aparelho para envio de notificacoes push.
- De uso: registros de acesso para fins de seguranca.

2. Para que usamos
- Autenticacao e seguranca do app.
- Exibir suas informacoes de plano e faturas.
- Atender chamados que voce abrir.
- Enviar notificacoes relacionadas ao seu servico.

3. Compartilhamento
Seus dados nao sao vendidos. Compartilhamos apenas com:
- Parceiros operacionais estritamente necessarios (ex: provedor de SMS/WhatsApp).
- Autoridades, em caso de obrigacao legal.

4. Seguranca
Dados sensiveis (CPF, telefone) sao armazenados de forma criptografada. Senhas sao armazenadas como hash, nunca em texto puro.

5. Seus direitos (LGPD)
Voce pode:
- Confirmar a existencia de tratamento.
- Acessar, corrigir e atualizar seus dados pelo perfil do app.
- Excluir sua conta — opcao "Excluir minha conta" em Perfil.
- Pedir portabilidade ou esclarecimentos em contato@ondelinetelecom.com.br.

6. Retencao
Mantemos seus dados enquanto voce for cliente ativo. Apos exclusao da conta, seus dados pessoais sao anonimizados, preservando apenas o historico operacional minimo exigido por lei.

7. Cookies / rastreio
O app nao usa cookies. Nao rastreia voce fora dele.

8. Contato do encarregado (DPO)
dpo@ondelinetelecom.com.br''';
