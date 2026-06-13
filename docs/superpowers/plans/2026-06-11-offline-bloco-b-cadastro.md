# Offline Bloco B (Cadastro offline) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Cadastrar cliente offline (rascunho local, payload-only) + enviar com 1 toque na lista de Clientes; planos cacheados; CPF como idempotência. Só app.

**Tech Stack:** Flutter, Riverpod, Dio, path_provider (já no projeto), connectivity_status (Bloco A).

> **Ambiente:** sem Flutter local — analyze no deploy. Commit `--no-verify`. Stay on `main`. Sem teste automatizado (file IO + UI). Cadastro NÃO tem fotos no fluxo (são pós-criação no detalhe) → rascunho é só payload.

---

## File Structure
- **Create:** `lib/core/sync/planos_cache.dart`, `lib/core/sync/cadastro_draft_repo.dart`, `lib/features/clientes/widgets/cadastro_drafts_sheet.dart`.
- **Modify:** `lib/core/sync/prefetch_service.dart` (prefetch planos); `lib/features/clientes/cliente_form_data.dart` (planos cache fallback + `criarFromJson`); `lib/features/clientes/cliente_novo_screen.dart` (submit offline); `lib/features/clientes/clientes_list_screen.dart` (banner).

---

### Task 1: Planos offline

- [ ] **Step 1: `lib/core/sync/planos_cache.dart`**
```dart
import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

Future<File> _planosCacheFile() async {
  final dir = await getApplicationDocumentsDirectory();
  return File(p.join(dir.path, 'planos_cache.json'));
}

/// Salva o JSON cru da resposta de /sgp/planos (shape {planos:[...]}).
Future<void> writePlanosCache(Object? raw) async {
  try {
    await (await _planosCacheFile()).writeAsString(jsonEncode(raw));
  } catch (_) {/* best-effort */}
}

/// Lê o JSON cru cacheado (mesmo shape de /sgp/planos) ou null.
Future<Map<String, dynamic>?> readPlanosCache() async {
  try {
    final f = await _planosCacheFile();
    if (!await f.exists()) return null;
    return (jsonDecode(await f.readAsString()) as Map).cast<String, dynamic>();
  } catch (_) {
    return null;
  }
}
```

- [ ] **Step 2: `planosProvider` cacheia + cai no cache** (`lib/features/clientes/cliente_form_data.dart`)

Adicionar imports: `import 'dart:async';` (pra `unawaited`) e `import '../../core/sync/planos_cache.dart';`. Substituir o corpo do `planosProvider`:
```dart
final planosProvider = FutureProvider.autoDispose<List<SgpPlano>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final r = await dio.get('/api/v1/sgp/planos');
    unawaited(writePlanosCache(r.data)); // aquece p/ offline
    return _decodeSgpPlanos(r.data);
  } on DioException catch (e) {
    if (_shouldFallbackToConfiguredPlans(e)) {
      try {
        final fallback = await dio.get('/api/v1/planos');
        return _decodeConfiguredPlanos(fallback.data);
      } on DioException {
        final cached = await readPlanosCache();
        if (cached != null) return _decodeSgpPlanos(cached);
        rethrow;
      }
    }
    final cached = await readPlanosCache();
    if (cached != null) return _decodeSgpPlanos(cached);
    rethrow;
  }
});
```

- [ ] **Step 3: PrefetchService aquece planos** (`lib/core/sync/prefetch_service.dart`)

Adicionar `import 'planos_cache.dart';`. Em `prefetchAll()`, depois de `await _prefetchClientes(userId);`, adicionar `await _prefetchPlanos();`. E o método:
```dart
  Future<void> _prefetchPlanos() async {
    try {
      final r = await _dio.get('/api/v1/sgp/planos');
      await writePlanosCache(r.data);
    } catch (e) {
      developer.log('prefetch planos falhou',
          name: 'PrefetchService', error: e);
    }
  }
```

- [ ] **Step 4: Commit**
```bash
git add lib/core/sync/planos_cache.dart lib/core/sync/prefetch_service.dart lib/features/clientes/cliente_form_data.dart
git commit --no-verify -m "feat(tecnico-mobile): planos SGP cacheados p/ cadastro offline"
```

---

### Task 2: DraftRepo + `criarFromJson`

- [ ] **Step 1: `lib/core/sync/cadastro_draft_repo.dart`**
```dart
import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// Rascunho de cadastro de cliente salvo localmente (offline). Só payload —
/// o cadastro não tem fotos no fluxo (fotos são anexadas no detalhe, online).
class CadastroDraft {
  final String id;
  final DateTime createdAt;
  final String cpf;
  final String nome;
  final Map<String, dynamic> payload;

  CadastroDraft({
    required this.id,
    required this.createdAt,
    required this.cpf,
    required this.nome,
    required this.payload,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'created_at': createdAt.toIso8601String(),
        'cpf': cpf,
        'nome': nome,
        'payload': payload,
      };

  factory CadastroDraft.fromJson(Map<String, dynamic> j) => CadastroDraft(
        id: j['id'] as String,
        createdAt:
            DateTime.tryParse(j['created_at'] as String? ?? '') ?? DateTime.now(),
        cpf: (j['cpf'] ?? '') as String,
        nome: (j['nome'] ?? '') as String,
        payload: (j['payload'] as Map).cast<String, dynamic>(),
      );
}

class CadastroDraftRepo {
  Future<Directory> _dir() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(docs.path, 'cadastro_drafts'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<CadastroDraft> save({
    required Map<String, dynamic> payload,
    required String cpf,
    required String nome,
  }) async {
    final id = DateTime.now().microsecondsSinceEpoch.toString();
    final draft = CadastroDraft(
      id: id,
      createdAt: DateTime.now(),
      cpf: cpf,
      nome: nome,
      payload: payload,
    );
    final dir = await _dir();
    await File(p.join(dir.path, '$id.json'))
        .writeAsString(jsonEncode(draft.toJson()));
    return draft;
  }

  Future<List<CadastroDraft>> list() async {
    final dir = await _dir();
    final entries = await dir.list().toList();
    final drafts = <CadastroDraft>[];
    for (final e in entries) {
      if (e is! File || !e.path.endsWith('.json')) continue;
      try {
        drafts.add(CadastroDraft.fromJson(
            (jsonDecode(await e.readAsString()) as Map).cast<String, dynamic>()));
      } catch (_) {/* ignora arquivo corrompido */}
    }
    drafts.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return drafts;
  }

  Future<void> delete(String id) async {
    final f = File(p.join((await _dir()).path, '$id.json'));
    if (await f.exists()) await f.delete();
  }
}

final cadastroDraftRepoProvider =
    Provider<CadastroDraftRepo>((ref) => CadastroDraftRepo());

final cadastroDraftsProvider = FutureProvider<List<CadastroDraft>>(
  (ref) => ref.watch(cadastroDraftRepoProvider).list(),
);
```

- [ ] **Step 2: `criarFromJson` em `ClienteFormActions`** (`lib/features/clientes/cliente_form_data.dart`)

Trocar:
```dart
  Future<String> criar(CreateClienteCampoIn body) async {
    final r = await _dio.post(
      '/api/v1/clientes-campo',
      data: body.toJson(),
    );
    return (r.data as Map)['id'] as String;
  }
```
por:
```dart
  Future<String> criar(CreateClienteCampoIn body) => criarFromJson(body.toJson());

  /// Cria a partir do Map já serializado (usado pelo envio de rascunho offline).
  Future<String> criarFromJson(Map<String, dynamic> payload) async {
    final r = await _dio.post('/api/v1/clientes-campo', data: payload);
    return (r.data as Map)['id'] as String;
  }
```

- [ ] **Step 3: Commit**
```bash
git add lib/core/sync/cadastro_draft_repo.dart lib/features/clientes/cliente_form_data.dart
git commit --no-verify -m "feat(tecnico-mobile): CadastroDraftRepo (rascunho offline) + criarFromJson"
```

---

### Task 3: Submit offline (`cliente_novo_screen.dart`)

- [ ] **Step 1: Imports**
```dart
import '../../core/sync/cadastro_draft_repo.dart';
import '../../core/sync/connectivity_status.dart';
```

- [ ] **Step 2: Salvar rascunho quando offline**

No `_enviar`, logo APÓS o `final body = CreateClienteCampoIn(...)` (que termina em `materiais: materiais,\n      );`) e ANTES de `final actions = ref.read(clienteFormActionsProvider);`, inserir:
```dart
      // Offline → salva rascunho local em vez de tentar o POST (que ia falhar).
      final offline = ref.read(connectivityStatusProvider).value == false;
      if (offline) {
        await ref.read(cadastroDraftRepoProvider).save(
              payload: body.toJson(),
              cpf: onlyDigits(_cpf.text),
              nome: _nome.text.trim(),
            );
        ref.invalidate(cadastroDraftsProvider);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Cadastro salvo offline. Envie quando tiver sinal.'),
          ),
        );
        context.go('/clientes');
        return;
      }
```

- [ ] **Step 3: Fallback rascunho em erro de rede no envio online**

No bloco `on DioException catch (e) {` do `_enviar`, no INÍCIO do catch (antes do `final body = e.response?.data;`), inserir:
```dart
      final isNetwork = e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.sendTimeout ||
          e.type == DioExceptionType.receiveTimeout;
      if (isNetwork) {
        await ref.read(cadastroDraftRepoProvider).save(
              payload: body.toJson(),
              cpf: onlyDigits(_cpf.text),
              nome: _nome.text.trim(),
            );
        ref.invalidate(cadastroDraftsProvider);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Sem conexão — cadastro salvo offline pra enviar depois.'),
          ),
        );
        context.go('/clientes');
        return;
      }
```
NOTA: `body` precisa estar no escopo do catch. Hoje `body` é declarado dentro do `try`. Mover a declaração do `final body = CreateClienteCampoIn(...)` (e o `materiais`) pra ANTES do `try` NÃO — em vez disso, como o catch não enxerga `body`, declarar `late CreateClienteCampoIn body;` antes do `try` e atribuir dentro. Ajuste: trocar `final body = CreateClienteCampoIn(` por `body = CreateClienteCampoIn(` e adicionar `late CreateClienteCampoIn body;` logo antes do `try {`. (O `materiais` pode ficar dentro do try.) Assim o catch acessa `body`.

- [ ] **Step 4: Commit**
```bash
git add lib/features/clientes/cliente_novo_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): cadastro salva rascunho offline (sem rede)"
```

---

### Task 4: Banner + sheet de envio

- [ ] **Step 1: `lib/features/clientes/widgets/cadastro_drafts_sheet.dart`**
```dart
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/sync/cadastro_draft_repo.dart';
import '../../../core/sync/connectivity_status.dart';
import '../../../core/ui/app_surfaces.dart';
import '../cliente_data.dart';
import '../cliente_form_data.dart';

/// Banner clicável na lista de Clientes mostrando cadastros pendentes.
class CadastroDraftsBanner extends StatelessWidget {
  const CadastroDraftsBanner({super.key, required this.count, required this.onTap});
  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: AppSurfaceCard(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: const Color(0xFFF59E0B).withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.cloud_upload_rounded,
                  size: 18, color: Color(0xFFB45309)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                '$count cadastro${count == 1 ? '' : 's'} pendente${count == 1 ? '' : 's'} de envio',
                style: const TextStyle(
                    fontWeight: FontWeight.w700, color: Color(0xFFB45309)),
              ),
            ),
            Icon(Icons.chevron_right, color: scheme.onSurfaceVariant),
          ],
        ),
      ),
    );
  }
}

Future<void> showCadastroDraftsSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => const _CadastroDraftsSheet(),
  );
}

class _CadastroDraftsSheet extends ConsumerStatefulWidget {
  const _CadastroDraftsSheet();
  @override
  ConsumerState<_CadastroDraftsSheet> createState() =>
      _CadastroDraftsSheetState();
}

class _CadastroDraftsSheetState extends ConsumerState<_CadastroDraftsSheet> {
  String? _enviandoId;

  void _toast(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  Future<void> _enviar(CadastroDraft d) async {
    setState(() => _enviandoId = d.id);
    try {
      await ref.read(clienteFormActionsProvider).criarFromJson(d.payload);
      await _concluir(d, 'Cliente cadastrado.');
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      final detail = (e.response?.data is Map
              ? (e.response!.data as Map)['detail']?.toString()
              : null) ??
          '';
      final dl = detail.toLowerCase();
      if (code == 409 && (dl.contains('cpf') || dl.contains('existe'))) {
        await _concluir(d, 'Cliente já estava cadastrado.');
      } else {
        _toast(detail.isNotEmpty
            ? detail
            : 'Não consegui enviar agora. Tente de novo.');
      }
    } catch (_) {
      _toast('Não consegui enviar agora. Tente de novo.');
    } finally {
      if (mounted) setState(() => _enviandoId = null);
    }
  }

  Future<void> _concluir(CadastroDraft d, String msg) async {
    await ref.read(cadastroDraftRepoProvider).delete(d.id);
    ref.invalidate(cadastroDraftsProvider);
    ref.invalidate(clientesListProvider);
    _toast(msg);
  }

  Future<void> _descartar(CadastroDraft d) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Descartar rascunho?'),
        content: Text('O cadastro de ${d.nome} não será enviado.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Descartar')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(cadastroDraftRepoProvider).delete(d.id);
    ref.invalidate(cadastroDraftsProvider);
  }

  @override
  Widget build(BuildContext context) {
    final drafts = ref.watch(cadastroDraftsProvider).value ?? const [];
    final online = ref.watch(connectivityStatusProvider).value ?? true;
    final mq = MediaQuery.of(context);
    return Padding(
      padding: EdgeInsets.only(bottom: mq.viewInsets.bottom + 16, top: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('Cadastros pendentes',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          if (!online)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('Conecte-se pra enviar.',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
            ),
          const SizedBox(height: 12),
          Flexible(
            child: ListView.separated(
              shrinkWrap: true,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: drafts.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final d = drafts[i];
                final enviando = _enviandoId == d.id;
                return AppSurfaceCard(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(d.nome,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text('CPF ${d.cpf}',
                                style: const TextStyle(
                                    fontSize: 12, color: Colors.grey)),
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: 'Descartar',
                        icon: const Icon(Icons.delete_outline),
                        onPressed: enviando ? null : () => _descartar(d),
                      ),
                      FilledButton(
                        onPressed:
                            (online && !enviando) ? () => _enviar(d) : null,
                        child: enviando
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2))
                            : const Text('Enviar'),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Banner na lista de Clientes** (`lib/features/clientes/clientes_list_screen.dart`)

Adicionar import: `import 'widgets/cadastro_drafts_sheet.dart';` (e `import 'cliente_data.dart';` já existe). No `CustomScrollView`, logo APÓS o sliver do chip de offline (e antes do KPI), inserir:
```dart
            if ((ref.watch(cadastroDraftsProvider).value ?? const []).isNotEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: CadastroDraftsBanner(
                    count: ref.watch(cadastroDraftsProvider).value!.length,
                    onTap: () => showCadastroDraftsSheet(context),
                  ),
                ),
              ),
```

- [ ] **Step 3: Commit**
```bash
git add lib/features/clientes/widgets/cadastro_drafts_sheet.dart lib/features/clientes/clientes_list_screen.dart
git commit --no-verify -m "feat(tecnico-mobile): banner + sheet de cadastros offline pendentes (enviar/descartar)"
```

---

### Task 5: Verificação

- [ ] **Step 1: Analyze (deploy)** — `flutter analyze lib/core/sync/ lib/features/clientes/` → limpo.
- [ ] **Step 2: Teste on-device:**
  - Online: abrir "Novo cliente" (carrega planos/materiais) → fechar.
  - Modo avião → "Novo cliente" → planos vêm do cache, materiais do cache → preencher → Salvar → toast "salvo offline" → volta pra lista com banner "1 pendente".
  - Religar rede → lista mostra banner → tocar → sheet → Enviar → cliente criado, rascunho some, lista atualiza.
  - Reenviar mesmo CPF (forçar) → "Cliente já estava cadastrado" (sem duplicar).
  - Descartar → some sem enviar.

---

## Self-Review

**Spec coverage:**
- Planos cache + prefetch + fallback → Task 1. ✅
- `CadastroDraftRepo` file-based payload-only + providers → Task 2 Step 1. ✅
- `criarFromJson` (online intacto via `criar`) → Task 2 Step 2. ✅
- Submit offline (conectividade) + fallback rede no envio online → Task 3. ✅
- Banner na lista + sheet (enviar 1-toque c/ 409-CPF=sucesso, 409-saldo/erro mantém; descartar) → Task 4. ✅
- Sem fotos no rascunho (descoberta) → refletido. ✅

**Placeholder scan:** sem TBD; código completo. (Único ajuste descritivo: `late CreateClienteCampoIn body;` no Task 3 Step 3 — instrução explícita.)

**Type consistency:** `criarFromJson(Map<String,dynamic>)` usado no sheet com `d.payload`; `cadastroDraftsProvider`/`cadastroDraftRepoProvider`/`connectivityStatusProvider`/`clientesListProvider` consistentes; `CadastroDraft.payload` é `Map<String,dynamic>` = body.toJson(); `onlyDigits`/`_cpf`/`_nome` no escopo do `_enviar`.
