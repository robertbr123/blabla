import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/branding/brand_bottom_nav.dart';
import '../clientes/clientes_list_screen.dart';
import '../estoque/estoque_screen.dart';
import '../os/os_list_screen.dart';
import '../perfil/perfil_screen.dart';

/// Shell com BottomNavigationBar — 4 tabs: OS / Estoque / Clientes / Perfil.
/// Detalhes (OS, Cliente, etc) abrem por cima do shell (push).
///
/// Troca de aba é puramente local (PageController) — não chama `context.go`
/// pra não empilhar transição de rota por cima da animação do PageView.
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

  Future<void> _select(int index) async {
    if (index == _index) return;
    setState(() => _index = index);
    if (!_pageController.hasClients) return;
    await _pageController.animateToPage(
      index,
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
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
          ? Padding(
              padding: const EdgeInsets.only(bottom: 64),
              child: FloatingActionButton.extended(
                onPressed: () => context.push('/clientes/novo'),
                icon: const Icon(Icons.person_add),
                label: const Text('Novo'),
              ),
            )
          : null,
      bottomNavigationBar: BrandBottomNav(
        selectedIndex: _index,
        onSelect: _select,
        items: const [
          BrandNavItem(
            icon: Icons.assignment_outlined,
            selectedIcon: Icons.assignment_rounded,
            label: 'OS',
          ),
          BrandNavItem(
            icon: Icons.inventory_2_outlined,
            selectedIcon: Icons.inventory_2_rounded,
            label: 'Estoque',
          ),
          BrandNavItem(
            icon: Icons.people_outline,
            selectedIcon: Icons.people_rounded,
            label: 'Clientes',
          ),
          BrandNavItem(
            icon: Icons.person_outline,
            selectedIcon: Icons.person_rounded,
            label: 'Perfil',
          ),
        ],
      ),
    );
  }
}
