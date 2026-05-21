import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../clientes/clientes_list_screen.dart';
import '../estoque/estoque_screen.dart';
import '../os/os_list_screen.dart';
import '../perfil/perfil_screen.dart';

/// Shell com BottomNavigationBar — 4 tabs: OS / Estoque / Clientes / Perfil.
/// Detalhes (OS, Cliente, etc) abrem por cima do shell (push).
class MainShell extends ConsumerStatefulWidget {
  final int initialTab;
  const MainShell({super.key, this.initialTab = 0});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  late int _index;
  late final PageController _pageController;

  static const _telas = [
    OsListScreen(),
    EstoqueScreen(),
    ClientesListScreen(),
    PerfilScreen(),
  ];

  static const _rotas = ['/os', '/estoque', '/clientes', '/perfil'];

  @override
  void initState() {
    super.initState();
    _index = widget.initialTab;
    _pageController = PageController(initialPage: _index);
  }

  @override
  void didUpdateWidget(covariant MainShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialTab == _index) return;
    _index = widget.initialTab;
    if (_pageController.hasClients) {
      _pageController.jumpToPage(_index);
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: PageView(
        controller: _pageController,
        physics: const NeverScrollableScrollPhysics(),
        onPageChanged: (index) {
          if (!mounted || index == _index) return;
          setState(() => _index = index);
        },
        children: _telas,
      ),
      floatingActionButton: _index == 2
          ? FloatingActionButton.extended(
              onPressed: () => context.push('/clientes/novo'),
              icon: const Icon(Icons.person_add),
              label: const Text('Novo'),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        animationDuration: const Duration(milliseconds: 420),
        onDestinationSelected: (index) async {
          if (index == _index) return;
          setState(() => _index = index);
          await _pageController.animateToPage(
            index,
            duration: const Duration(milliseconds: 320),
            curve: Curves.easeOutCubic,
          );
          if (!mounted) return;
          context.go(_rotas[index]);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.inventory_2_outlined),
            selectedIcon: Icon(Icons.inventory_2),
            label: 'Estoque',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Clientes',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Perfil',
          ),
        ],
      ),
    );
  }
}
