# Sinal + IP no detalhe do cliente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Resumo compacto de sinal (RX) + GPON + IP no detalhe do cliente (seção Conexão), reusando `redeDiagnosticoProvider`.

**Tech Stack:** Flutter, Riverpod. Sem backend, sem provider novo.

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`. Sem teste automatizado (UI/provider).

---

## File Structure
- **Modify:** `lib/features/clientes/cliente_detail_screen.dart` — import `rede_data`, inserir `_SinalResumo` no `_SecaoConexao`, + helpers `_corRx`/`_idadeLeitura` + a classe `_SinalResumo`.

---

### Task 1: Sinal/IP no detalhe

**Files:** Modify `lib/features/clientes/cliente_detail_screen.dart`

- [ ] **Step 1: Import**

Adicionar junto aos outros imports de feature:
```dart
import '../rede/rede_data.dart';
```

- [ ] **Step 2: Inserir o `_SinalResumo` no `_SecaoConexao`**

No `Column` do `_SecaoConexao`, ANTES do `Padding` do botão "Gerenciar rede WiFi", inserir:
```dart
          _SinalResumo(cpf: cliente.cpf),
```
(Fica entre as linhas de PPPoE e o `Padding(...OutlinedButton "Gerenciar rede WiFi")`.)

- [ ] **Step 3: Adicionar a classe `_SinalResumo` + helpers**

Logo após a classe `_SecaoConexao` (antes de `_SecaoInstalacao`), adicionar:
```dart
/// Régua de cor do RX (GPON, dBm) — mesma da tela de Rede.
/// (Duplicação leve; cleanup futuro pode extrair um helper compartilhado.)
Color _corRx(double? rx) {
  if (rx == null) return Colors.grey;
  if (rx > -8 || rx < -27) return Colors.red;
  if (rx < -25) return Colors.orange;
  return Colors.green;
}

String _idadeLeitura(DateTime? t) {
  if (t == null) return '—';
  final d = DateTime.now().difference(t);
  if (d.inMinutes < 1) return 'agora';
  if (d.inMinutes < 60) return 'há ${d.inMinutes} min';
  if (d.inHours < 24) return 'há ${d.inHours} h';
  return 'há ${d.inDays} ${d.inDays == 1 ? 'dia' : 'dias'}';
}

/// Resumo compacto do sinal/IP no detalhe (auto-carrega via redeDiagnosticoProvider).
class _SinalResumo extends ConsumerWidget {
  final String cpf;
  const _SinalResumo({required this.cpf});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final diag = ref.watch(redeDiagnosticoProvider(cpf));

    Widget muted(String text) => Text(
          text,
          style: TextStyle(fontSize: 13, color: scheme.onSurfaceVariant),
        );

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: diag.when(
        loading: () => Row(
          children: [
            const SizedBox(
              height: 14,
              width: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 8),
            muted('Carregando sinal…'),
          ],
        ),
        error: (_, __) => muted('Sinal indisponível.'),
        data: (d) {
          final s = d.sinal;
          if (!d.encontrada || s == null) return muted('Sinal indisponível.');
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.circle, size: 12, color: _corRx(s.rxPower)),
                  const SizedBox(width: 8),
                  Text(
                    'RX: ${s.rxPower?.toStringAsFixed(1) ?? '—'} dBm',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 16),
                  Flexible(
                    child: Text(
                      'GPON: ${s.statusGpon ?? '—'}',
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: scheme.onSurfaceVariant),
                    ),
                  ),
                ],
              ),
              if (s.ipExterno != null) ...[
                const SizedBox(height: 4),
                muted('IP: ${s.ipExterno}'),
              ],
              const SizedBox(height: 4),
              Text(
                'última leitura ${_idadeLeitura(d.lastInform)}',
                style: TextStyle(fontSize: 11, color: scheme.onSurfaceVariant),
              ),
            ],
          );
        },
      ),
    );
  }
}
```

- [ ] **Step 4: Conferir imports**

`ConsumerWidget`/`WidgetRef` vêm de `flutter_riverpod` (já importado — o screen usa). `Colors`/`Icons` de material (já). `redeDiagnosticoProvider`/`Diagnostico`/`SinalFibra` do `rede_data.dart` (Step 1).

- [ ] **Step 5: Analyze (deploy)**

Run: `flutter analyze lib/features/clientes/cliente_detail_screen.dart`
Expected: `No issues found!`.

- [ ] **Step 6: Commit**
```bash
git add lib/features/clientes/cliente_detail_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): sinal (RX) + GPON + IP no detalhe do cliente"
```

---

### Task 2: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/features/clientes/cliente_detail_screen.dart` → limpo.
- [ ] **Step 2: On-device:**
  - Abrir um cliente com ONU online → seção Conexão mostra "Carregando sinal…" e depois RX colorido + GPON + IP + "última leitura há X".
  - Cliente sem ONU / sem rede → "Sinal indisponível." (resto do detalhe ok).
  - Botão "Gerenciar rede WiFi" segue funcionando.

---

## Self-Review

**Spec coverage:**
- `_SinalResumo` ConsumerWidget em `_SecaoConexao`, auto via `redeDiagnosticoProvider` → Steps 2-3. ✅
- Compacto: RX colorido + GPON + IP + última leitura → Step 3. ✅
- Estados loading/error/indisponível → Step 3. ✅
- Helpers `_corRx`/`_idadeLeitura` locais → Step 3. ✅
- `_SecaoConexao` segue StatelessWidget (filho ConsumerWidget) → Step 2. ✅

**Placeholder scan:** sem TBD; código completo.

**Type consistency:** `redeDiagnosticoProvider(String)` → `Diagnostico { encontrada, lastInform, sinal: SinalFibra{rxPower, statusGpon, ipExterno} }`; `_corRx(double?)`; `cliente.cpf` é String.
