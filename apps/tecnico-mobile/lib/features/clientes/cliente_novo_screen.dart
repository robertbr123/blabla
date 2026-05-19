import 'package:flutter/material.dart';

/// Placeholder — sera substituido pelo form completo na Fase 6.
class ClienteNovoScreen extends StatelessWidget {
  const ClienteNovoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Novo cliente')),
      body: const Padding(
        padding: EdgeInsets.all(24),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.construction, size: 56),
              SizedBox(height: 12),
              Text(
                'Tela de cadastro em construção — Fase 6.',
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 6),
              Text(
                'Form em 3 steps com GPS, ViaCEP, planos SGP, materiais e fotos.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
