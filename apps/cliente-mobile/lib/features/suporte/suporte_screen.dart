import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/os_repository.dart';
import '../../core/branding/brand_tokens.dart';
import 'chat_tab.dart';
import 'widgets/os_card.dart';

class SuporteScreen extends ConsumerStatefulWidget {
  const SuporteScreen({super.key});

  @override
  ConsumerState<SuporteScreen> createState() => _SuporteScreenState();
}

class _SuporteScreenState extends ConsumerState<SuporteScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Suporte'),
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline_rounded),
            tooltip: 'Perguntas frequentes',
            onPressed: () => context.push('/faq'),
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          labelColor: BrandTokens.primary,
          unselectedLabelColor: BrandTokens.textSecondary,
          indicatorColor: BrandTokens.primary,
          tabs: const [
            Tab(text: 'Chat'),
            Tab(text: 'Meus chamados'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const [
          ChatTab(),
          _ChamadosTab(),
        ],
      ),
      // FAB logo acima da navbar flutuante, colado mas sem encostar.
      // Navbar interna ~62px + margem 16 do MainShell = ~78. Padding 70
      // deixa o FAB ~8px acima da borda superior da navbar.
      floatingActionButton: Padding(
        padding: EdgeInsets.only(
          bottom: 70 + MediaQuery.of(context).padding.bottom,
        ),
        child: AnimatedBuilder(
          animation: _tabs,
          builder: (_, __) => _tabs.index == 1
              ? FloatingActionButton.extended(
                  onPressed: () => context.push('/suporte/novo'),
                  icon: const Icon(Icons.add),
                  label: const Text('Novo chamado'),
                  backgroundColor: BrandTokens.primary,
                  foregroundColor: Colors.white,
                )
              : const SizedBox.shrink(),
        ),
      ),
    );
  }
}

class _ChamadosTab extends ConsumerWidget {
  const _ChamadosTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(osListProvider);
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(osListProvider);
        await ref.read(osListProvider.future);
      },
      child: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Erro carregando chamados')),
        data: (list) {
          if (list.isEmpty) {
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                const SizedBox(height: 96),
                Padding(
                  padding: const EdgeInsets.all(BrandTokens.spaceXl),
                  child: Column(
                    children: [
                      const Icon(Icons.inbox_outlined,
                          size: 64, color: BrandTokens.textSecondary),
                      const SizedBox(height: BrandTokens.spaceMd),
                      Text(
                        'Nenhum chamado ainda',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: BrandTokens.spaceSm),
                      Text(
                        'Toque em "Novo chamado" pra abrir um.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: BrandTokens.textSecondary,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            itemCount: list.length,
            itemBuilder: (_, i) => OsCard(os: list[i]),
          );
        },
      ),
    );
  }
}
