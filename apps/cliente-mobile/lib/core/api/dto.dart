class MeDto {
  MeDto({
    required this.id,
    required this.nome,
    required this.cpfLast4,
    required this.telefone,
    this.email,
    required this.biometricEnabled,
    this.planoNome,
    this.statusConexao,
    this.contratos = const [],
    this.aniversarianteDoMes = false,
    this.aniversarioDiaMes,
  });

  factory MeDto.fromJson(Map<String, dynamic> j) => MeDto(
        id: j['id'] as String,
        nome: j['nome'] as String,
        cpfLast4: j['cpf_last4'] as String,
        telefone: j['telefone'] as String,
        email: j['email'] as String?,
        biometricEnabled: j['biometric_enabled'] as bool,
        planoNome: j['plano_nome'] as String?,
        statusConexao: j['status_conexao'] as String?,
        contratos: ((j['contratos'] as List?) ?? const [])
            .map((c) => ContratoResumoDto.fromJson(c as Map<String, dynamic>))
            .toList(),
        aniversarianteDoMes: (j['aniversariante_do_mes'] as bool?) ?? false,
        aniversarioDiaMes: j['aniversario_dia_mes'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'nome': nome,
        'cpf_last4': cpfLast4,
        'telefone': telefone,
        'email': email,
        'biometric_enabled': biometricEnabled,
        'plano_nome': planoNome,
        'status_conexao': statusConexao,
        'contratos': contratos.map((c) => c.toJson()).toList(),
        'aniversariante_do_mes': aniversarianteDoMes,
        'aniversario_dia_mes': aniversarioDiaMes,
      };

  final String id;
  final String nome;
  final String cpfLast4;
  final String telefone;
  final String? email;
  final bool biometricEnabled;
  final String? planoNome;
  final String? statusConexao;
  final List<ContratoResumoDto> contratos;
  final bool aniversarianteDoMes;
  final String? aniversarioDiaMes;

  bool get temMultiContrato => contratos.length > 1;
}

class ContratoResumoDto {
  ContratoResumoDto({
    required this.id,
    required this.plano,
    required this.status,
    this.cidade = '',
    this.bairro = '',
    this.logradouro = '',
    this.numero = '',
  });

  factory ContratoResumoDto.fromJson(Map<String, dynamic> j) =>
      ContratoResumoDto(
        id: j['id'] as String,
        plano: j['plano'] as String? ?? '',
        status: j['status'] as String? ?? '',
        cidade: j['cidade'] as String? ?? '',
        bairro: j['bairro'] as String? ?? '',
        logradouro: j['logradouro'] as String? ?? '',
        numero: j['numero'] as String? ?? '',
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'plano': plano,
        'status': status,
        'cidade': cidade,
        'bairro': bairro,
        'logradouro': logradouro,
        'numero': numero,
      };

  final String id;
  final String plano;
  final String status;
  final String cidade;
  final String bairro;
  final String logradouro;
  final String numero;

  /// "Rua Tal, 123 — Bairro" ou cidade como fallback.
  String get enderecoResumido {
    final partes = <String>[];
    if (logradouro.isNotEmpty) {
      partes.add(numero.isNotEmpty ? '$logradouro, $numero' : logradouro);
    }
    if (bairro.isNotEmpty) partes.add(bairro);
    if (partes.isEmpty && cidade.isNotEmpty) return cidade;
    return partes.join(' — ');
  }

  /// Apelido curto pro chip do switcher (bairro ou cidade).
  String get apelidoCurto {
    if (bairro.isNotEmpty) return bairro;
    if (cidade.isNotEmpty) return cidade;
    return plano;
  }
}

class EnderecoDto {
  EnderecoDto({
    this.logradouro = '',
    this.numero = '',
    this.bairro = '',
    this.cidade = '',
    this.uf = '',
    this.cep = '',
  });
  factory EnderecoDto.fromJson(Map<String, dynamic> j) => EnderecoDto(
        logradouro: (j['logradouro'] ?? '') as String,
        numero: (j['numero'] ?? '') as String,
        bairro: (j['bairro'] ?? '') as String,
        cidade: (j['cidade'] ?? '') as String,
        uf: (j['uf'] ?? '') as String,
        cep: (j['cep'] ?? '') as String,
      );
  Map<String, dynamic> toJson() => {
        'logradouro': logradouro,
        'numero': numero,
        'bairro': bairro,
        'cidade': cidade,
        'uf': uf,
        'cep': cep,
      };

  final String logradouro;
  final String numero;
  final String bairro;
  final String cidade;
  final String uf;
  final String cep;

  String get linhaUnica {
    final partes = [
      if (logradouro.isNotEmpty) logradouro,
      if (numero.isNotEmpty) numero,
      if (bairro.isNotEmpty) bairro,
      if (cidade.isNotEmpty) cidade,
      if (uf.isNotEmpty) uf,
    ];
    return partes.join(', ');
  }
}

class ContratoDto {
  ContratoDto({
    required this.id,
    required this.plano,
    required this.status,
    this.cidade = '',
    required this.endereco,
  });
  factory ContratoDto.fromJson(Map<String, dynamic> j) => ContratoDto(
        id: j['id'] as String,
        plano: j['plano'] as String,
        status: j['status'] as String,
        cidade: (j['cidade'] ?? '') as String,
        endereco: EnderecoDto.fromJson(j['endereco'] as Map<String, dynamic>),
      );
  Map<String, dynamic> toJson() => {
        'id': id,
        'plano': plano,
        'status': status,
        'cidade': cidade,
        'endereco': endereco.toJson(),
      };

  final String id;
  final String plano;
  final String status;
  final String cidade;
  final EnderecoDto endereco;
}

class PlanoDto {
  PlanoDto({
    required this.nomeTitular,
    required this.contratos,
    required this.enderecoPrincipal,
  });
  factory PlanoDto.fromJson(Map<String, dynamic> j) => PlanoDto(
        nomeTitular: j['nome_titular'] as String,
        contratos: ((j['contratos'] as List?) ?? const [])
            .map((c) => ContratoDto.fromJson(c as Map<String, dynamic>))
            .toList(),
        enderecoPrincipal: EnderecoDto.fromJson(
            j['endereco_principal'] as Map<String, dynamic>),
      );
  Map<String, dynamic> toJson() => {
        'nome_titular': nomeTitular,
        'contratos': contratos.map((c) => c.toJson()).toList(),
        'endereco_principal': enderecoPrincipal.toJson(),
      };

  final String nomeTitular;
  final List<ContratoDto> contratos;
  final EnderecoDto enderecoPrincipal;
}

class ChatMessageDto {
  ChatMessageDto({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
  });
  factory ChatMessageDto.fromJson(Map<String, dynamic> j) => ChatMessageDto(
        id: j['id'] as String,
        role: j['role'] as String,
        content: j['content'] as String,
        createdAt: DateTime.parse(j['created_at'] as String),
      );

  final String id;
  final String role; // "user" | "bot"
  final String content;
  final DateTime createdAt;

  bool get isUser => role == 'user';
}

class OsDto {
  OsDto({
    required this.id,
    required this.tipo,
    required this.descricao,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.npsSolicitadoEm,
    this.npsRespondidoEm,
    this.npsScore,
  });
  factory OsDto.fromJson(Map<String, dynamic> j) => OsDto(
        id: j['id'] as String,
        tipo: j['tipo'] as String,
        descricao: j['descricao'] as String,
        status: j['status'] as String,
        createdAt: DateTime.parse(j['created_at'] as String),
        updatedAt: DateTime.parse(j['updated_at'] as String),
        npsSolicitadoEm: j['nps_solicitado_em'] != null
            ? DateTime.parse(j['nps_solicitado_em'] as String)
            : null,
        npsRespondidoEm: j['nps_respondido_em'] != null
            ? DateTime.parse(j['nps_respondido_em'] as String)
            : null,
        npsScore: j['nps_score'] as int?,
      );
  final String id;
  final String tipo; // sem_internet|mudanca_endereco|troca_plano
  final String descricao;
  final String status; // aberto|em_atendimento|concluido|cancelado
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? npsSolicitadoEm;
  final DateTime? npsRespondidoEm;
  final int? npsScore;

  bool get npsPendente =>
      status == 'concluido' &&
      npsSolicitadoEm != null &&
      npsRespondidoEm == null;

  String get tipoLabel => switch (tipo) {
        'sem_internet' => 'Sem internet',
        'mudanca_endereco' => 'Mudanca de endereco',
        'troca_plano' => 'Troca de plano',
        _ => tipo,
      };
}

class ContatoOperadoraDto {
  ContatoOperadoraDto({
    required this.id,
    required this.tipo,
    required this.label,
    required this.valor,
    this.subtitle,
    required this.ordem,
  });

  factory ContatoOperadoraDto.fromJson(Map<String, dynamic> j) =>
      ContatoOperadoraDto(
        id: j['id'] as String,
        tipo: j['tipo'] as String,
        label: j['label'] as String,
        valor: j['valor'] as String,
        subtitle: j['subtitle'] as String?,
        ordem: (j['ordem'] as int?) ?? 0,
      );

  final String id;
  final String tipo; // whatsapp|telefone|email|endereco|instagram|facebook|site|outro
  final String label;
  final String valor;
  final String? subtitle;
  final int ordem;
}

class ManutencaoBreakingDto {
  ManutencaoBreakingDto({
    required this.id,
    required this.titulo,
    this.descricao,
    required this.inicioAt,
    required this.fimAt,
  });

  factory ManutencaoBreakingDto.fromJson(Map<String, dynamic> j) =>
      ManutencaoBreakingDto(
        id: j['id'] as String,
        titulo: j['titulo'] as String,
        descricao: j['descricao'] as String?,
        inicioAt: DateTime.parse(j['inicio_at'] as String),
        fimAt: DateTime.parse(j['fim_at'] as String),
      );

  final String id;
  final String titulo;
  final String? descricao;
  final DateTime inicioAt;
  final DateTime fimAt;
}

class FaturaDto {
  FaturaDto({
    required this.id,
    required this.valor,
    required this.vencimento,
    required this.status,
    this.diasAtraso = 0,
    required this.temPdf,
    required this.temPix,
  });
  factory FaturaDto.fromJson(Map<String, dynamic> j) => FaturaDto(
        id: j['id'] as String,
        valor: (j['valor'] as num).toDouble(),
        vencimento: j['vencimento'] as String,
        status: j['status'] as String,
        diasAtraso: (j['dias_atraso'] as int?) ?? 0,
        temPdf: j['tem_pdf'] as bool,
        temPix: j['tem_pix'] as bool,
      );

  final String id;
  final double valor;
  final String vencimento;
  final String status;
  final int diasAtraso;
  final bool temPdf;
  final bool temPix;

  bool get isAberto => status == 'aberto';
  bool get isVencido => isAberto && diasAtraso > 0;

  DateTime get vencimentoDate => DateTime.parse(vencimento);
}

class AvisoDto {
  AvisoDto({
    required this.id,
    required this.titulo,
    required this.corpo,
    required this.severidade,
    required this.publicadoEm,
  });
  factory AvisoDto.fromJson(Map<String, dynamic> j) => AvisoDto(
        id: j['id'] as String,
        titulo: j['titulo'] as String,
        corpo: j['corpo'] as String,
        severidade: j['severidade'] as String,
        publicadoEm: DateTime.parse(j['publicado_em'] as String),
      );
  final String id;
  final String titulo;
  final String corpo;
  final String severidade;
  final DateTime publicadoEm;
}

class PromocaoDto {
  PromocaoDto({
    required this.id,
    required this.titulo,
    required this.subtitulo,
    required this.imagemUrl,
    required this.ctaLabel,
    required this.ctaAction,
    required this.tipo,
    required this.gradientFrom,
    required this.gradientTo,
    required this.icon,
  });

  factory PromocaoDto.fromJson(Map<String, dynamic> j) => PromocaoDto(
        id: j['id'] as String,
        titulo: j['titulo'] as String,
        subtitulo: (j['subtitulo'] as String?) ?? '',
        imagemUrl: j['imagem_url'] as String?,
        ctaLabel: (j['cta_label'] as String?) ?? 'Saiba mais',
        ctaAction: (j['cta_action'] as String?) ?? 'info',
        tipo: (j['tipo'] as String?) ?? 'generica',
        gradientFrom: j['gradient_from'] as String?,
        gradientTo: j['gradient_to'] as String?,
        icon: j['icon'] as String?,
      );

  final String id;
  final String titulo;
  final String subtitulo;
  final String? imagemUrl;
  final String ctaLabel;
  /// "info" | "url:<https>" | "tela:<rota>"
  final String ctaAction;
  /// "generica" | "indicacao"
  final String tipo;
  final String? gradientFrom;
  final String? gradientTo;
  /// Nome do icone Material (mapeado em promo_icon.dart).
  final String? icon;
}

class IndicacaoMeuDto {
  IndicacaoMeuDto({
    required this.codigo,
    required this.linkCompartilhamento,
    required this.numeroEmpresa,
    required this.usos,
    required this.convertidos,
    required this.creditoAplicado,
  });
  factory IndicacaoMeuDto.fromJson(Map<String, dynamic> j) => IndicacaoMeuDto(
        codigo: j['codigo'] as String,
        linkCompartilhamento: (j['link_compartilhamento'] as String?) ?? '',
        numeroEmpresa: (j['numero_empresa'] as String?) ?? '',
        usos: (j['usos'] as int?) ?? 0,
        convertidos: (j['convertidos'] as int?) ?? 0,
        creditoAplicado: (j['credito_aplicado'] as int?) ?? 0,
      );
  final String codigo;
  final String linkCompartilhamento;
  final String numeroEmpresa;
  final int usos;
  final int convertidos;
  final int creditoAplicado;
}

class ConexaoDto {
  ConexaoDto({
    required this.status,
    required this.motivo,
    required this.plano,
    required this.cidade,
    required this.temTelemetriaReal,
  });
  factory ConexaoDto.fromJson(Map<String, dynamic> j) => ConexaoDto(
        status: j['status'] as String? ?? 'desconhecido',
        motivo: (j['motivo'] as String?) ?? '',
        plano: j['plano'] as String?,
        cidade: j['cidade'] as String?,
        temTelemetriaReal: (j['tem_telemetria_real'] as bool?) ?? false,
      );
  /// 'ativo' | 'suspenso' | 'cancelado' | 'desconhecido'
  final String status;
  final String motivo;
  final String? plano;
  final String? cidade;
  final bool temTelemetriaReal;
}

class NotificacaoDto {
  NotificacaoDto({
    required this.id,
    required this.categoria,
    required this.titulo,
    required this.corpo,
    required this.action,
    required this.lida,
    required this.createdAt,
  });
  factory NotificacaoDto.fromJson(Map<String, dynamic> j) => NotificacaoDto(
        id: j['id'] as String,
        categoria: j['categoria'] as String,
        titulo: j['titulo'] as String,
        corpo: (j['corpo'] as String?) ?? '',
        action: j['action'] as String?,
        lida: (j['lida'] as bool?) ?? false,
        createdAt: DateTime.parse(j['created_at'] as String),
      );
  final String id;
  /// fatura | os | manutencao | promocao | conta | outro
  final String categoria;
  final String titulo;
  final String corpo;
  /// "tela:/path" | "url:https://..." | null
  final String? action;
  final bool lida;
  final DateTime createdAt;
}

class NotifPrefsDto {
  NotifPrefsDto({required this.categorias});
  factory NotifPrefsDto.fromJson(Map<String, dynamic> j) {
    final map = (j['categorias'] as Map?) ?? {};
    return NotifPrefsDto(
      categorias: map.map((k, v) => MapEntry(k as String, v as bool)),
    );
  }
  Map<String, dynamic> toJson() => {'categorias': categorias};
  final Map<String, bool> categorias;
}
