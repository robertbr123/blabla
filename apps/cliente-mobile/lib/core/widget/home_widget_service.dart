import 'dart:io';

import 'package:home_widget/home_widget.dart';
import 'package:intl/intl.dart';

import '../api/dto.dart';

/// Facade pra atualizar o widget de home screen com dados frescos.
///
/// Chamado de pontos-chave da app (após /me, após /faturas, após /conexao).
/// Em iOS, [HomeWidget.updateWidget] não faz nada até que o WidgetKit (Swift)
/// seja implementado numa onda futura — então iOS recebe os saves mas não
/// renderiza.
class HomeWidgetService {
  static const _kStatus = 'status_conexao';
  static const _kProxFaturaValor = 'proxima_fatura_valor';
  static const _kProxFaturaVencimento = 'proxima_fatura_vencimento';

  static const _androidProvider = 'ClienteWidgetProvider';
  static const _iosName = 'ClienteWidget';

  static final _moedaFmt = NumberFormat.currency(
    locale: 'pt_BR',
    symbol: 'R\$',
    decimalDigits: 2,
  );

  /// Atualiza status de conexão. Aceita nulo pra limpar.
  static Future<void> setStatus(String? status) async {
    await HomeWidget.saveWidgetData<String>(_kStatus, status);
  }

  /// Atualiza próxima fatura (a com vencimento mais próximo no futuro,
  /// ou a aberta mais antiga se houver atraso). Passe null pra zerar.
  static Future<void> setProximaFatura(FaturaDto? fatura) async {
    if (fatura == null) {
      await HomeWidget.saveWidgetData<String>(_kProxFaturaValor, null);
      await HomeWidget.saveWidgetData<String>(_kProxFaturaVencimento, null);
      return;
    }
    final valor = _moedaFmt.format(fatura.valor);
    final venc = _formatVencimento(fatura);
    await HomeWidget.saveWidgetData<String>(_kProxFaturaValor, valor);
    await HomeWidget.saveWidgetData<String>(_kProxFaturaVencimento, venc);
  }

  /// Dispara repaint do widget (Android). Idempotente.
  static Future<void> refresh() async {
    if (!Platform.isAndroid) return;
    await HomeWidget.updateWidget(
      name: _androidProvider,
      androidName: _androidProvider,
      iOSName: _iosName,
    );
  }

  /// Helper combinado: dado o snapshot mais recente, atualiza tudo e força
  /// repaint. Não falha se algum passo der erro (best-effort).
  static Future<void> sync({
    String? status,
    FaturaDto? proximaFatura,
  }) async {
    try {
      await setStatus(status);
      await setProximaFatura(proximaFatura);
      await refresh();
    } on Object {
      // Widget é cosmético — falha silenciosa pra não atrapalhar UX principal.
    }
  }

  static String _formatVencimento(FaturaDto f) {
    try {
      final v = DateTime.parse(f.vencimento);
      final hoje = DateTime.now();
      final diff = v.difference(DateTime(hoje.year, hoje.month, hoje.day)).inDays;
      final fmt = DateFormat('dd/MM', 'pt_BR');
      if (f.status == 'aberto' && diff < 0) {
        return 'Vencida em ${fmt.format(v)}';
      }
      if (diff == 0) return 'Vence hoje';
      if (diff == 1) return 'Vence amanhã';
      if (diff > 1 && diff <= 7) return 'Vence em $diff dias';
      return 'Vence em ${fmt.format(v)}';
    } on Object {
      return 'Venc ${f.vencimento}';
    }
  }
}
