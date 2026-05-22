import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/branding/brand_tokens.dart';
import '../faturas/faturas_screen.dart';
import '../home/home_screen.dart';
import '../perfil/perfil_screen.dart';
import '../suporte/suporte_screen.dart';

/// Indice da tab ativa do MainShell. Outras telas podem pular tabs
/// setando `ref.read(mainShellTabProvider.notifier).state = N`.
/// 0=Inicio, 1=Faturas, 2=Suporte, 3=Perfil.
final mainShellTabProvider = StateProvider<int>((ref) => 0);

class MainShell extends ConsumerWidget {
  const MainShell({super.key});

  static const _tabs = [
    HomeScreen(),
    FaturasScreen(),
    SuporteScreen(),
    PerfilScreen(),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final index = ref.watch(mainShellTabProvider);
    return Scaffold(
      body: IndexedStack(index: index, children: _tabs),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          indicatorColor: BrandTokens.primary.withOpacity(0.10),
          labelTextStyle: WidgetStatePropertyAll(
            Theme.of(context).textTheme.labelSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
        ),
        child: NavigationBar(
          selectedIndex: index,
          onDestinationSelected: (i) =>
              ref.read(mainShellTabProvider.notifier).state = i,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Inicio',
            ),
            NavigationDestination(
              icon: Icon(Icons.receipt_long_outlined),
              selectedIcon: Icon(Icons.receipt_long),
              label: 'Faturas',
            ),
            NavigationDestination(
              icon: Icon(Icons.support_agent_outlined),
              selectedIcon: Icon(Icons.support_agent),
              label: 'Suporte',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Perfil',
            ),
          ],
        ),
      ),
    );
  }
}
