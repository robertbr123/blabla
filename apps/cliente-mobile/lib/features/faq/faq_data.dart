/// Conteudo estatico da FAQ. Sem backend — atualizacoes saem em deploy.
/// Mantido in-app pra reduzir tickets antes do cliente abrir OS.
class FaqCategoria {
  const FaqCategoria({
    required this.id,
    required this.titulo,
    required this.icon,
    required this.artigos,
  });
  final String id;
  final String titulo;
  /// Nome do icone Material (mapeado em faq_icon.dart).
  final String icon;
  final List<FaqArtigo> artigos;
}

class FaqArtigo {
  const FaqArtigo({
    required this.id,
    required this.titulo,
    required this.resumo,
    required this.passos,
  });
  final String id;
  final String titulo;
  final String resumo;
  /// Lista de paragrafos / passos (markdown-lite suportado: linhas comecando
  /// com "•" viram bullets).
  final List<String> passos;
}

const faqCategorias = <FaqCategoria>[
  FaqCategoria(
    id: 'conexao',
    titulo: 'Conexao',
    icon: 'wifi',
    artigos: [
      FaqArtigo(
        id: 'sem-internet',
        titulo: 'Estou sem internet, o que faco?',
        resumo: 'Checklist rapido antes de abrir um chamado.',
        passos: [
          'Confira as luzes do seu roteador:',
          '• Power (verde): roteador ligado.',
          '• PON / Internet (verde fixa): sinal da fibra OK.',
          '• PON piscando ou apagada: provavelmente cabo da rua afetado.',
          'Desligue o roteador da tomada, aguarde 30 segundos e ligue novamente.',
          'Teste a conexao em outro dispositivo (notebook ou outro celular).',
          'Se nada resolver, abra um chamado pelo app que enviamos um tecnico.',
        ],
      ),
      FaqArtigo(
        id: 'lenta',
        titulo: 'Minha internet esta lenta',
        resumo: 'Causas comuns e como melhorar.',
        passos: [
          'Wi-Fi sofre com paredes e distancia. Se possivel, conecte por cabo pra testar.',
          'Muitos dispositivos conectados ao mesmo tempo dividem a banda.',
          'Apps de streaming em alta resolucao ou downloads consomem muito.',
          'Faca um teste de velocidade conectado por cabo pra ver se chega no contratado.',
          'Se chegar por cabo mas nao por Wi-Fi, o problema e o sinal Wi-Fi — considere instalar repetidores.',
          'Se nao chegar nem por cabo, fale com o suporte.',
        ],
      ),
      FaqArtigo(
        id: 'wifi-senha',
        titulo: 'Esqueci a senha do meu Wi-Fi',
        resumo: 'Como recuperar ou trocar.',
        passos: [
          'A senha padrao geralmente esta na etiqueta do roteador.',
          'Pra trocar a senha voce precisa acessar o painel admin do roteador (192.168.0.1 ou 192.168.1.1 no navegador).',
          'Login e senha de admin tambem estao na etiqueta — geralmente "admin" / "admin".',
          'Se nao conseguir, abra um chamado que orientamos por chat.',
        ],
      ),
    ],
  ),
  FaqCategoria(
    id: 'faturas',
    titulo: 'Faturas',
    icon: 'payment',
    artigos: [
      FaqArtigo(
        id: 'pagar-pix',
        titulo: 'Como pagar minha fatura por Pix',
        resumo: 'Pix copia-e-cola ou QR code dentro do app.',
        passos: [
          'Vai em "Faturas" no menu inferior.',
          'Toca na fatura aberta — abre a janela com o codigo Pix.',
          'Voce pode escanear o QR code direto pelo seu app do banco.',
          'Ou tocar em "Copiar codigo Pix" e colar no app do banco.',
          'Pagamento e confirmado automaticamente em alguns minutos.',
        ],
      ),
      FaqArtigo(
        id: 'segunda-via',
        titulo: 'Quero a 2a via do boleto',
        resumo: 'Boleto em PDF disponivel no app.',
        passos: [
          'Vai em "Faturas" no menu inferior.',
          'Toca na fatura desejada.',
          'Toca em "Abrir boleto em PDF" — abre no seu visualizador.',
          'Voce pode salvar o PDF no celular ou compartilhar.',
        ],
      ),
      FaqArtigo(
        id: 'pagamento-nao-aparece',
        titulo: 'Paguei mas o app ainda mostra como em aberto',
        resumo: 'Tempo de atualizacao do sistema.',
        passos: [
          'Pagamentos por Pix podem levar ate 2h pra aparecer no app.',
          'Pagamentos por boleto podem levar ate 3 dias uteis.',
          'Voce nao precisa avisar — assim que o banco compensar, a fatura muda pra "Paga" automaticamente.',
          'Se ja passou esse prazo, abra um chamado com comprovante.',
        ],
      ),
    ],
  ),
  FaqCategoria(
    id: 'conta',
    titulo: 'Conta',
    icon: 'account',
    artigos: [
      FaqArtigo(
        id: 'mudar-senha',
        titulo: 'Como troco minha senha do app',
        resumo: 'Pelo proprio Perfil.',
        passos: [
          'Vai em "Perfil" no menu inferior.',
          'Toca em "Mudar senha".',
          'Informa a senha atual e a nova senha (minimo 8 caracteres).',
        ],
      ),
      FaqArtigo(
        id: 'mudar-telefone',
        titulo: 'Mudei de numero — como atualizo?',
        resumo: 'Pelo Perfil voce edita seu telefone.',
        passos: [
          'Vai em "Perfil" no menu inferior.',
          'Toca em "Telefone" e digita o novo numero.',
          'Voce vai precisar confirmar com um codigo enviado no WhatsApp novo.',
        ],
      ),
      FaqArtigo(
        id: 'excluir-conta',
        titulo: 'Como excluo minha conta do app',
        resumo: 'Acao reversivel — voce pode criar conta de novo.',
        passos: [
          'Vai em "Perfil" no menu inferior, role ate o final.',
          'Toca em "Excluir minha conta".',
          'Seus dados pessoais sao anonimizados — voce continua sendo cliente Ondeline.',
          'Se quiser usar o app de novo, basta criar conta com seu CPF.',
        ],
      ),
    ],
  ),
  FaqCategoria(
    id: 'plano',
    titulo: 'Plano',
    icon: 'speed',
    artigos: [
      FaqArtigo(
        id: 'mudar-plano',
        titulo: 'Quero mudar meu plano',
        resumo: 'Solicitamos atraves do suporte.',
        passos: [
          'Hoje a troca de plano e feita via suporte — em breve direto no app.',
          'Abra um chamado pelo app na opcao "Mudar plano" ou fale no chat.',
          'Um atendente vai te apresentar as opcoes disponiveis pra sua regiao.',
        ],
      ),
      FaqArtigo(
        id: 'velocidade-real',
        titulo: 'A velocidade entregue e a mesma do plano?',
        resumo: 'Sim, mas medir corretamente importa.',
        passos: [
          'A velocidade contratada e o maximo no cabo do roteador.',
          'No Wi-Fi voce sempre vai medir um pouco menos por causa do meio sem fio.',
          'Pra medir corretamente: conecte um cabo de rede do roteador no notebook e use speedtest.net.',
          'Pequenas variacoes (5-10%) sao normais. Se estiver muito abaixo, fale com suporte.',
        ],
      ),
    ],
  ),
];
