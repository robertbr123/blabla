/// Modo dev — bypass de login pra visualizar telas sem rede.
///
/// Quando ativo:
/// - `apiClientProvider` intercepta requests e devolve mocks
/// - Splash redireciona pra /home direto
/// - Logout limpa a flag e volta pro fluxo normal
library;

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../auth/auth_storage.dart';

const _kDevMode = 'dev_mode';

class DevModeController extends ChangeNotifier {
  bool _enabled = false;
  bool get enabled => _enabled;

  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    _enabled = p.getBool(_kDevMode) ?? false;
    notifyListeners();
  }

  Future<void> enable() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool(_kDevMode, true);
    await writeAccessToken('dev-mode-fake-token');
    await writeSession(
      cpfLast4: '0000',
      nome: 'Cliente Demo',
      biometricEnabled: false,
    );
    _enabled = true;
    notifyListeners();
  }

  Future<void> disable() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_kDevMode);
    _enabled = false;
    notifyListeners();
  }
}

final devModeProvider = ChangeNotifierProvider<DevModeController>((ref) {
  final c = DevModeController();
  c.load();
  return c;
});

/// Mock responses pra endpoints da API quando devMode esta ativo.
Map<String, dynamic>? mockResponse(String method, String path) {
  if (kReleaseMode) return null; // nunca em release
  if (method == 'GET' && path == '/api/v1/cliente-app/me') {
    return _mockMe;
  }
  if (method == 'GET' && path == '/api/v1/cliente-app/plano') {
    return _mockPlano;
  }
  if (method == 'GET' && path == '/api/v1/cliente-app/avisos') {
    return {'items': []};
  }
  if (method == 'GET' && path == '/api/v1/cliente-app/faturas') {
    return {'items': _mockFaturas};
  }
  if (method == 'GET' && path == '/api/v1/cliente-app/os') {
    return {'items': _mockOsList};
  }
  if (method == 'POST' && path == '/api/v1/cliente-app/os') {
    return _mockOsCriado;
  }
  if (method == 'PATCH' && path == '/api/v1/cliente-app/me') {
    return _mockMe;
  }
  if (path.startsWith('/api/v1/cliente-app/faturas/') && path.endsWith('/pix')) {
    return {'codigo': '00020126580014BR.GOV.BCB.PIX0136demo-pix-copia-e-cola-fake5204000053039865802BR'};
  }
  if (path.startsWith('/api/v1/cliente-app/faturas/') &&
      path.endsWith('/boleto')) {
    return {'url': 'https://example.com/demo-boleto.pdf'};
  }
  return null;
}

const _mockMe = {
  'id': 'demo-uuid-0000',
  'nome': 'Cliente Demo',
  'cpf_last4': '0000',
  'telefone': '92981234567',
  'email': 'demo@ondeline.test',
  'biometric_enabled': false,
  'plano_nome': 'Fibra 600 Mega',
  'status_conexao': 'online',
};

const _mockPlano = {
  'nome_titular': 'Cliente Demo',
  'contratos': [
    {
      'id': 'c-demo',
      'plano': 'Fibra 600 Mega',
      'status': 'ativo',
      'cidade': 'Manaus',
      'endereco': {
        'logradouro': 'Av Demo',
        'numero': '100',
        'bairro': 'Centro',
        'cidade': 'Manaus',
        'uf': 'AM',
        'cep': '69000-000',
      },
    },
  ],
  'endereco_principal': {
    'logradouro': 'Av Demo',
    'numero': '100',
    'bairro': 'Centro',
    'cidade': 'Manaus',
    'uf': 'AM',
    'cep': '69000-000',
  },
};

const _mockFaturas = [
  {
    'id': 't-demo-1',
    'valor': 129.90,
    'vencimento': '2026-06-10',
    'status': 'aberto',
    'dias_atraso': 0,
    'tem_pdf': true,
    'tem_pix': true,
  },
  {
    'id': 't-demo-2',
    'valor': 129.90,
    'vencimento': '2026-05-10',
    'status': 'pago',
    'dias_atraso': 0,
    'tem_pdf': true,
    'tem_pix': false,
  },
  {
    'id': 't-demo-3',
    'valor': 129.90,
    'vencimento': '2026-04-10',
    'status': 'pago',
    'dias_atraso': 0,
    'tem_pdf': true,
    'tem_pix': false,
  },
];

final _mockOsList = [
  {
    'id': 'os-demo-1',
    'tipo': 'sem_internet',
    'descricao': 'Internet caiu desde ontem a noite. Reiniciei o modem mas nao volta.',
    'status': 'em_atendimento',
    'created_at': DateTime.now().subtract(const Duration(hours: 6)).toIso8601String(),
    'updated_at': DateTime.now().subtract(const Duration(hours: 2)).toIso8601String(),
  },
  {
    'id': 'os-demo-2',
    'tipo': 'troca_plano',
    'descricao': 'Quero subir pra fibra 1 giga',
    'status': 'concluido',
    'created_at': DateTime.now().subtract(const Duration(days: 5)).toIso8601String(),
    'updated_at': DateTime.now().subtract(const Duration(days: 4)).toIso8601String(),
  },
];

final _mockOsCriado = {
  'id': 'os-demo-novo',
  'tipo': 'sem_internet',
  'descricao': 'Demo',
  'status': 'aberto',
  'created_at': DateTime.now().toIso8601String(),
  'updated_at': DateTime.now().toIso8601String(),
};
