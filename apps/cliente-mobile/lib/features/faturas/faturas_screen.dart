import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/dto.dart';
import '../../core/api/faturas_repository.dart';
import '../../core/branding/brand_tokens.dart';
import 'widgets/fatura_bottom_sheet.dart';
import 'widgets/fatura_card.dart';

class FaturasScreen extends ConsumerStatefulWidget {
  const FaturasScreen({super.key});

  @override
  ConsumerState<FaturasScreen> createState() => _FaturasScreenState();
}

class _FaturasScreenState extends ConsumerState<FaturasScreen>
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
        title: const Text('Faturas'),
        bottom: TabBar(
          controller: _tabs,
          labelColor: BrandTokens.primary,
          unselectedLabelColor: BrandTokens.textSecondary,
          indicatorColor: BrandTokens.primary,
          tabs: const [
            Tab(text: 'Em aberto'),
            Tab(text: 'Pagas'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [
          _FaturasList(provider: faturasAbertasProvider),
          _FaturasList(provider: faturasPagasProvider),
        ],
      ),
    );
  }
}

class _FaturasList extends ConsumerWidget {
  const _FaturasList({required this.provider});
  final FutureProvider<List<FaturaDto>> provider;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(provider);
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(provider);
        await ref.read(provider.future);
      },
      child: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _Empty(
          icon: Icons.error_outline,
          title: 'Nao consegui carregar suas faturas',
          subtitle: 'Verifique sua conexao e tente de novo.',
        ),
        data: (faturas) {
          if (faturas.isEmpty) {
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: const [
                SizedBox(height: 96),
                _Empty(
                  icon: Icons.receipt_long_outlined,
                  title: 'Nada por aqui',
                  subtitle: 'Voce esta em dia.',
                ),
              ],
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.all(BrandTokens.spaceLg),
            itemCount: faturas.length,
            itemBuilder: (_, i) {
              final f = faturas[i];
              return FaturaCard(
                fatura: f,
                onTap: () => FaturaBottomSheet.show(context, f),
              );
            },
          );
        },
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({
    required this.icon,
    required this.title,
    required this.subtitle,
  });
  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(BrandTokens.spaceXl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 64, color: BrandTokens.textSecondary),
            const SizedBox(height: BrandTokens.spaceMd),
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: BrandTokens.spaceSm),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: BrandTokens.textSecondary,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
