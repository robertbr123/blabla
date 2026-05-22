import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/conexao_repository.dart';
import '../../core/api/dto.dart';
import '../../core/api/faturas_repository.dart';
import '../../core/api/os_repository.dart';
import '../../core/notifications/push_service.dart';
import '../../core/widget/home_widget_service.dart';
import '../faturas/faturas_screen.dart';
import '../home/home_screen.dart';
import '../perfil/perfil_screen.dart';
import '../suporte/suporte_screen.dart';
import 'widgets/floating_nav_bar.dart';

/// Indice da tab ativa do MainShell. Outras telas podem pular tabs
/// setando `ref.read(mainShellTabProvider.notifier).state = N`.
/// 0=Inicio, 1=Faturas, 2=Suporte, 3=Perfil.
final mainShellTabProvider = StateProvider<int>((ref) => 0);

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  static const _tabs = [
    HomeScreen(),
    FaturasScreen(),
    SuporteScreen(),
    PerfilScreen(),
  ];

  @override
  void initState() {
    super.initState();
    // Registra push token no backend assim que o user chega ao shell
    // (= autenticado). Idempotente, falha silenciosa sem Firebase.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(pushServiceProvider).start();
    });
  }

  @override
  Widget build(BuildContext context) {
    final index = ref.watch(mainShellTabProvider);

    // Badge faturas: ponto vermelho se houver vencida.
    final temFaturaVencida = ref.watch(faturasAbertasProvider).maybeWhen(
          data: (l) => l.any((f) => f.isVencido),
          orElse: () => false,
        );

    // Badge suporte: contagem de OS abertas/em atendimento.
    final osAbertasCount = ref.watch(osListProvider).maybeWhen(
          data: (l) => l
              .where((o) =>
                  o.status == 'aberto' || o.status == 'em_atendimento')
              .length,
          orElse: () => 0,
        );

    // Sincroniza widget de home screen com dados atuais (best-effort).
    // Roda toda vez que faturas/conexão chegam — barato e mantém widget vivo.
    ref.listen<AsyncValue<List<FaturaDto>>>(faturasAbertasProvider, (_, next) {
      next.whenData((faturas) {
        HomeWidgetService.setProximaFatura(_proximaFatura(faturas))
            .then((_) => HomeWidgetService.refresh());
      });
    });
    ref.listen<AsyncValue<ConexaoDto>>(conexaoProvider, (_, next) {
      next.whenData((c) {
        HomeWidgetService.setStatus(c.status)
            .then((_) => HomeWidgetService.refresh());
      });
    });

    return Scaffold(
      extendBody: true,
      body: IndexedStack(index: index, children: _tabs),
      bottomNavigationBar: FloatingNavBar(
        currentIndex: index,
        onTap: (i) => ref.read(mainShellTabProvider.notifier).state = i,
        items: [
          const FloatingNavItem(
            icon: Icons.home_outlined,
            selectedIcon: Icons.home_rounded,
            label: 'Início',
          ),
          FloatingNavItem(
            icon: Icons.receipt_long_outlined,
            selectedIcon: Icons.receipt_long,
            label: 'Faturas',
            badgeDot: temFaturaVencida,
          ),
          FloatingNavItem(
            icon: Icons.support_agent_outlined,
            selectedIcon: Icons.support_agent,
            label: 'Suporte',
            badgeCount: osAbertasCount,
          ),
          const FloatingNavItem(
            icon: Icons.person_outline,
            selectedIcon: Icons.person,
            label: 'Perfil',
          ),
        ],
      ),
    );
  }

  /// Escolhe a fatura "destaque" pro widget:
  /// 1) primeira vencida (urgência maior),
  /// 2) próxima com vencimento mais cedo no futuro,
  /// 3) se não houver abertas, null.
  static FaturaDto? _proximaFatura(List<FaturaDto> abertas) {
    if (abertas.isEmpty) return null;
    final vencidas = abertas.where((f) => f.isVencido).toList()
      ..sort((a, b) => a.vencimento.compareTo(b.vencimento));
    if (vencidas.isNotEmpty) return vencidas.first;
    final ordenadas = [...abertas]
      ..sort((a, b) => a.vencimento.compareTo(b.vencimento));
    return ordenadas.first;
  }
}
