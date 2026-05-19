import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../estoque/estoque_screen.dart';
import '../os/os_list_screen.dart';
import '../perfil/perfil_screen.dart';

/// Shell com BottomNavigationBar pra trocar entre OS e Estoque.
/// Detalhe da OS abre por cima do shell (push em vez de tab).
class MainShell extends ConsumerStatefulWidget {
  final int initialTab;
  const MainShell({super.key, this.initialTab = 0});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  late int _index;

  static const _telas = [
    OsListScreen(),
    EstoqueScreen(),
    PerfilScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _index = widget.initialTab;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _telas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) {
          setState(() => _index = i);
          context.go(['/os', '/estoque', '/perfil'][i]);
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment),
            label: 'OS',
          ),
          NavigationDestination(
            icon: Icon(Icons.inventory_2_outlined),
            selectedIcon: Icon(Icons.inventory_2),
            label: 'Estoque',
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
