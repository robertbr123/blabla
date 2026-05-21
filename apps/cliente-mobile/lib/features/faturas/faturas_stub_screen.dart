import 'package:flutter/material.dart';

import '../../core/branding/brand_tokens.dart';

class FaturasStubScreen extends StatelessWidget {
  const FaturasStubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Faturas')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceXl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.receipt_long_outlined,
                  size: 64, color: BrandTokens.textSecondary),
              const SizedBox(height: BrandTokens.spaceMd),
              Text(
                'Em breve',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: BrandTokens.spaceSm),
              Text(
                'Suas faturas, codigo PIX e boleto PDF chegam aqui na proxima atualizacao.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: BrandTokens.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
