import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/notificacoes_repository.dart';
import '../../../core/branding/brand_tokens.dart';

/// Sino com badge de unread count. Tap navega pra /notificacoes.
class NotifBell extends ConsumerWidget {
  const NotifBell({super.key, this.color});
  final Color? color;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificacoesUnreadCountProvider);
    final count = async.maybeWhen(data: (c) => c, orElse: () => 0);
    return Stack(
      clipBehavior: Clip.none,
      children: [
        IconButton(
          icon: Icon(
            Icons.notifications_outlined,
            color: color,
          ),
          tooltip: 'Notificações',
          onPressed: () => context.push('/notificacoes'),
        ),
        if (count > 0)
          Positioned(
            top: 6,
            right: 6,
            child: IgnorePointer(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 5,
                  vertical: 1,
                ),
                constraints: const BoxConstraints(
                  minWidth: 18,
                  minHeight: 18,
                ),
                decoration: BoxDecoration(
                  color: BrandTokens.danger,
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: Theme.of(context).brightness == Brightness.dark
                        ? BrandTokens.surfaceDark
                        : BrandTokens.surface,
                    width: 2,
                  ),
                ),
                child: Text(
                  count > 9 ? '9+' : '$count',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    height: 1.0,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
