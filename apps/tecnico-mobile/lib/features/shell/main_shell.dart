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
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _telas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) {
          setState(() => _index = i);
          context.go(_rotas[i]);
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
