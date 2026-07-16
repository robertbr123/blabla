import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/contatos_repository.dart';

/// Busca o contato de WhatsApp comercial com melhor esforço e abre o wa.me
/// com a [mensagem] informada. Retorna `true` se conseguiu localizar o
/// número e disparar o launch, `false` caso contrário (sem número/erro).
Future<bool> abrirWhatsappComercial(
  WidgetRef ref, {
  required String mensagem,
}) async {
  String? whatsNumber;
  try {
    final contatos = await ref.read(contatosOperadoraProvider.future);
    for (final c in contatos) {
      if (c.tipo == 'whatsapp') {
        final digits = c.valor.replaceAll(RegExp(r'\D'), '');
        if (digits.isNotEmpty) whatsNumber = digits;
        break;
      }
    }
  } on Object {
    whatsNumber = null;
  }
  if (whatsNumber == null) return false;
  final uri = Uri.parse(
    'https://wa.me/$whatsNumber'
    '?text=${Uri.encodeComponent(mensagem)}',
  );
  try {
    // launchUrl devolve false (sem lançar) quando o sistema recusa abrir —
    // propaga pro caller mostrar o aviso em vez de fingir sucesso.
    return await launchUrl(uri, mode: LaunchMode.externalApplication);
  } on Object {
    return false;
  }
}
