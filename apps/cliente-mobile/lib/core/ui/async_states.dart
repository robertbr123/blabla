import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../branding/brand_tokens.dart';

/// Card de erro padrão do app: mensagem amigável + retry.
class ErrorCard extends StatelessWidget {
  const ErrorCard({
    super.key,
    this.message = 'Não conseguimos carregar agora.',
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(BrandTokens.spaceLg),
      decoration: BoxDecoration(
        color: BrandTokens.danger.withValues(alpha: isDark ? 0.12 : 0.06),
        borderRadius: BorderRadius.circular(BrandTokens.radiusMd),
        border: Border.all(color: BrandTokens.danger.withValues(alpha: 0.25)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded,
              color: BrandTokens.danger, size: 32),
          const SizedBox(height: BrandTokens.spaceSm),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          if (onRetry != null) ...[
            const SizedBox(height: BrandTokens.spaceMd),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Tentar de novo'),
            ),
          ],
        ],
      ),
    );
  }
}

/// Estado vazio padrão: ícone grande suave + título + subtítulo.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
  });

  final IconData icon;
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final secondary = Theme.of(context).brightness == Brightness.dark
        ? BrandTokens.textSecondaryDark
        : BrandTokens.textSecondary;
    return Padding(
      padding: const EdgeInsets.all(BrandTokens.spaceXl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withValues(alpha: 0.10),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: BrandTokens.primary, size: 34),
          ),
          const SizedBox(height: BrandTokens.spaceMd),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: BrandTokens.spaceXs),
            Text(
              subtitle!,
              textAlign: TextAlign.center,
              style: TextStyle(color: secondary, fontSize: 13, height: 1.4),
            ),
          ],
        ],
      ),
    );
  }
}

/// Wrapper padrão pra AsyncValue: data → builder, loading → spinner
/// (ou skeleton custom), error → ErrorCard (ou custom).
class AsyncBuilder<T> extends StatelessWidget {
  const AsyncBuilder({
    super.key,
    required this.value,
    required this.builder,
    this.loading,
    this.error,
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final Widget? loading;
  final Widget? error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      data: builder,
      loading: () =>
          loading ??
          const Padding(
            padding: EdgeInsets.all(BrandTokens.spaceXl),
            child: Center(child: CircularProgressIndicator()),
          ),
      error: (_, __) => error ?? ErrorCard(onRetry: onRetry),
    );
  }
}
