import 'package:flutter/material.dart';

import '../../core/branding/brand_tokens.dart';

class SuporteStubScreen extends StatelessWidget {
  const SuporteStubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Suporte')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(BrandTokens.spaceXl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.support_agent_outlined,
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
                'Abertura de chamado e chat in-app chegam nas proximas atualizacoes.',
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
