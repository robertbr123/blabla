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
      };

  final String id;
  final String nome;
  final String cpfLast4;
  final String telefone;
  final String? email;
  final bool biometricEnabled;
  final String? planoNome;
  final String? statusConexao;
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

class OsDto {
  OsDto({
    required this.id,
    required this.tipo,
    required this.descricao,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });
  factory OsDto.fromJson(Map<String, dynamic> j) => OsDto(
        id: j['id'] as String,
        tipo: j['tipo'] as String,
        descricao: j['descricao'] as String,
        status: j['status'] as String,
        createdAt: DateTime.parse(j['created_at'] as String),
        updatedAt: DateTime.parse(j['updated_at'] as String),
      );
  final String id;
  final String tipo; // sem_internet|mudanca_endereco|troca_plano
  final String descricao;
  final String status; // aberto|em_atendimento|concluido|cancelado
  final DateTime createdAt;
  final DateTime updatedAt;

  String get tipoLabel => switch (tipo) {
        'sem_internet' => 'Sem internet',
        'mudanca_endereco' => 'Mudanca de endereco',
        'troca_plano' => 'Troca de plano',
        _ => tipo,
      };
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
