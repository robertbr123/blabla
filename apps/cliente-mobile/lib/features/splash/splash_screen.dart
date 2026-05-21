import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_state.dart';
import '../../core/branding/brand_tokens.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _decide());
  }

  Future<void> _decide() async {
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    final hasToken =
        await ref.read(hasTokenProvider.future).catchError((_) => false);
    if (!mounted) return;
    context.go(hasToken ? '/home' : '/onboarding/cpf');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: BrandTokens.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 84,
              height: 84,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(BrandTokens.radiusLg),
              ),
              alignment: Alignment.center,
              child: const Text(
                'O',
                style: TextStyle(
                  fontSize: 48,
                  fontWeight: FontWeight.w900,
                  color: BrandTokens.primary,
                ),
              ),
            ),
            const SizedBox(height: BrandTokens.spaceLg),
            const Text(
              'Ondeline',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
