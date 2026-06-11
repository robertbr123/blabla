import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

/// Banner colorido na Home quando o cliente faz aniversario neste mes.
///
/// Mostra: emoji + 'Feliz aniversário, X!' + 'Toque pra resgatar 5% off
/// na proxima fatura via WhatsApp'. Tap leva pra tela de contatos (ou
/// abre WhatsApp se houver entry tipo whatsapp).
///
/// Dispensavel pelo botao X (dismiss persiste pra nao chatear no mesmo mes).
class AniversarianteBanner extends ConsumerStatefulWidget {
  const AniversarianteBanner({super.key, required this.me});
  final MeDto me;

  @override
  ConsumerState<AniversarianteBanner> createState() =>
      _AniversarianteBannerState();
}

class _AniversarianteBannerState extends ConsumerState<AniversarianteBanner> {
  static const _keyDismissedMonth = 'aniv_banner_dismissed_month';
  bool _hidden = false;
  String? _dismissedKey;

  @override
  void initState() {
    super.initState();
    _loadDismiss();
  }

  String _currentKey() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}';
  }

  Future<void> _loadDismiss() async {
    final p = await SharedPreferences.getInstance();
    setState(() {
      _dismissedKey = p.getString(_keyDismissedMonth);
    });
  }

  Future<void> _dismiss() async {
    final p = await SharedPreferences.getInstance();
    final key = _currentKey();
    await p.setString(_keyDismissedMonth, key);
    if (!mounted) return;
    setState(() {
      _hidden = true;
      _dismissedKey = key;
    });
  }

  String _primeiroNome() {
    final t = widget.me.nome.trim();
    if (t.isEmpty) return '';
    final p = t.split(RegExp(r'\s+')).first;
    return p.isEmpty
        ? ''
        : p[0].toUpperCase() + p.substring(1).toLowerCase();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.me.aniversarianteDoMes) return const SizedBox.shrink();
    if (_hidden) return const SizedBox.shrink();
    if (_dismissedKey == _currentKey()) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
      child: InkWell(
        borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
        onTap: () => context.push('/contatos'),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: BrandTokens.spaceMd,
            vertical: 12,
          ),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [BrandTokens.accentPink, BrandTokens.accentOrange],
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
            ),
            borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
            boxShadow: [
              BoxShadow(
                color: BrandTokens.accentPink.withOpacity(0.30),
                blurRadius: 14,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            children: [
              const Text('🎂', style: TextStyle(fontSize: 28)),
              const SizedBox(width: BrandTokens.spaceSm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      _primeiroNome().isEmpty
                          ? 'Feliz aniversário!'
                          : 'Feliz aniversário, ${_primeiroNome()}!',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Toque pra resgatar 5% off na próxima fatura',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: BrandTokens.spaceXs),
              GestureDetector(
                onTap: _dismiss,
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.20),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.close_rounded,
                    color: Colors.white,
                    size: 16,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
