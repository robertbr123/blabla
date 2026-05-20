import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../theme.dart';
import 'app_surfaces.dart';

enum AppStatePanelTone { neutral, info, success, warning, danger }

class AppStatePanel extends StatelessWidget {
  const AppStatePanel({
    super.key,
    required this.title,
    required this.message,
    this.icon,
    this.progress,
    this.tone = AppStatePanelTone.neutral,
    this.actionLabel,
    this.onAction,
    this.detail,
    this.padding = const EdgeInsets.fromLTRB(20, 28, 20, 24),
  }) : assert(
          (actionLabel == null && onAction == null) ||
              (actionLabel != null && onAction != null),
          'actionLabel and onAction must be provided together',
        );

  const AppStatePanel.loading({
    super.key,
    required this.title,
    required this.message,
    this.detail,
    this.padding = const EdgeInsets.fromLTRB(20, 28, 20, 24),
  })  : tone = AppStatePanelTone.info,
        icon = null,
        progress = true,
        actionLabel = null,
        onAction = null;

  const AppStatePanel.empty({
    super.key,
    required this.title,
    required this.message,
    required this.icon,
    this.detail,
    this.actionLabel,
    this.onAction,
    this.tone = AppStatePanelTone.neutral,
    this.padding = const EdgeInsets.fromLTRB(20, 28, 20, 24),
  }) : progress = false;

  const AppStatePanel.error({
    super.key,
    required this.title,
    required this.message,
    this.detail,
    this.actionLabel,
    this.onAction,
    this.padding = const EdgeInsets.fromLTRB(20, 28, 20, 24),
  })  : tone = AppStatePanelTone.danger,
        icon = Icons.error_outline_rounded,
        progress = false;

  const AppStatePanel.offline({
    super.key,
    required this.title,
    required this.message,
    this.detail,
    this.actionLabel,
    this.onAction,
    this.padding = const EdgeInsets.fromLTRB(20, 28, 20, 24),
  })  : tone = AppStatePanelTone.warning,
        icon = Icons.wifi_off_rounded,
        progress = false;

  final String title;
  final String message;
  final String? detail;
  final IconData? icon;
  final bool? progress;
  final AppStatePanelTone tone;
  final String? actionLabel;
  final VoidCallback? onAction;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final colors = _resolveColors(scheme);

    return AppSurfaceCard(
      padding: padding,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: colors.background,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: colors.foreground.withValues(alpha: 0.14),
              ),
            ),
            alignment: Alignment.center,
            child: progress == true
                ? SizedBox(
                    width: 26,
                    height: 26,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.4,
                      color: colors.foreground,
                    ),
                  )
                : Icon(
                    icon,
                    size: 30,
                    color: colors.foreground,
                  ),
          ),
          const SizedBox(height: 18),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: scheme.onSurface,
              letterSpacing: -0.2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              height: 1.45,
              color: scheme.onSurfaceVariant,
            ),
          ),
          if (detail != null && detail!.trim().isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              detail!,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 12,
                height: 1.4,
                color: scheme.onSurfaceVariant,
              ),
            ),
          ],
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onAction,
              icon: Icon(progress == true ? Icons.sync : Icons.refresh_rounded),
              label: Text(actionLabel!),
            ),
          ],
        ],
      ),
    );
  }

  ({Color foreground, Color background}) _resolveColors(ColorScheme scheme) {
    final foreground = switch (tone) {
      AppStatePanelTone.info => scheme.primary,
      AppStatePanelTone.success => brandSuccess,
      AppStatePanelTone.warning => scheme.secondary,
      AppStatePanelTone.danger => scheme.error,
      AppStatePanelTone.neutral => scheme.onSurfaceVariant,
    };

    return (
      foreground: foreground,
      background: foreground.withValues(alpha: 0.10),
    );
  }
}

bool isOfflineException(Object error) {
  return error is DioException &&
      (error.type == DioExceptionType.connectionError ||
          error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.sendTimeout ||
          error.type == DioExceptionType.receiveTimeout);
}
