# App v3 — Imagem na landing + Triagem pré-chamado + Chat com rede — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Landing de promo mostra a imagem nítida; chamado "Sem internet" passa por varredura GenieACS (mostrada ao cliente, anexada ao chamado); chat in-app ganha a tool `consultar_rede_app` (read-only) via mini-loop de function-calling.

**Architecture:** Spec em `docs/superpowers/specs/2026-06-11-app-v3-imagem-triagem-chat-rede-design.md`. Fatia 1 = app-only (1 arquivo). Fatia 2 = app (wizard de chamado) + bloco na dashboard de OS; diagnóstico viaja no `payload_json` existente (sem migration). Fatia 3 = API-only (`cliente_app_chat.py` ganha tool loop leve, sem acoplamento com o pipeline do WhatsApp).

**Tech Stack:** Flutter 3.44/Riverpod; FastAPI + HermesProvider (OpenAI-compatible, já suporta tools); Next.js 15.

**Regras gerais:**
- Commits locais por task com **paths explícitos** (`git add <arquivos>` — NUNCA `git add .`; há sessão paralela no repo). **NUNCA git push** sem OK.
- Python: future import colado na docstring; sem anotação entre aspas (UP037); validar `uvx ruff check apps/api/src apps/api/tests` + mypy local (`apps/api/.venv/bin/mypy`). pytest só no CI.
- Flutter: `flutter analyze && flutter test`; `withValues(alpha:)`.
- Dashboard: `npx next build` (pnpm build tem problema pré-existente de approve-builds).

---

## FATIA 1 — Imagem em destaque na landing da promo

### Task 1: Hero da landing com imagem nítida

**Files:**
- Modify: `apps/cliente-mobile/lib/features/promocoes/promocao_detalhe_screen.dart`

- [ ] **Step 1: Trocar o background do FlexibleSpaceBar**

No `_Conteudo.build`, o `Hero` do `SliverAppBar` hoje tem Container com gradiente + `DecorationImage` opacity 0.35 + ícone central. Substituir o child do `Hero` por:

```dart
                child: Hero(
                  tag: 'promo-${promo.id}',
                  child: imagemAbs != null
                      // Promo com imagem: destaque nítido + scrim na base
                      // (legibilidade do título ao colapsar).
                      ? Container(
                          decoration: BoxDecoration(
                            image: DecorationImage(
                              image: NetworkImage(imagemAbs),
                              fit: BoxFit.cover,
                            ),
                          ),
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [
                                  Colors.transparent,
                                  Colors.black.withValues(alpha: 0.45),
                                ],
                                stops: const [0.55, 1.0],
                              ),
                            ),
                            child: const SizedBox.expand(),
                          ),
                        )
                      // Sem imagem: visual atual (gradiente + ícone).
                      : Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [from, to],
                            ),
                          ),
                          child: Center(
                            child: Container(
                              width: 88,
                              height: 88,
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.18),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                promoIconOf(promo.icon),
                                color: Colors.white,
                                size: 42,
                              ),
                            ),
                          ),
                        ),
                ),
```

(O `imagemAbs` já é calculado no método. Manter `backgroundColor: from` do SliverAppBar — vira o placeholder enquanto a imagem carrega.)

- [ ] **Step 2: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla/apps/cliente-mobile && flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/features/promocoes/promocao_detalhe_screen.dart
git commit -m "feat(app/promocoes): landing mostra imagem nitida em destaque (icone vira fallback)"
```

---

## FATIA 2 — Triagem antes do chamado Sem Internet

### Task 2: Widget de varredura + integração no wizard

**Files:**
- Create: `apps/cliente-mobile/lib/features/suporte/widgets/triagem_rede.dart`
- Modify: `apps/cliente-mobile/lib/features/suporte/novo_chamado_screen.dart`

- [ ] **Step 1: Conferir o repository de rede**

Grep em `lib/core/api/` por `rede` — já existe repository com métodos pros endpoints `/cliente-app/rede/status` e `/cliente-app/rede/aparelhos` (a tela `/rede` usa). Reusar os métodos/DTOs existentes (NÃO criar repository novo). Anotar os nomes reais no report.

- [ ] **Step 2: Criar `triagem_rede.dart`**

Widget `TriagemRede` (ConsumerStatefulWidget) com callback `onConcluir(Map<String, dynamic>? diagnostico)` e `onResolveu()`:

```dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/branding/brand_tokens.dart';
// + imports do repository/DTOs reais de rede (conferidos no Step 1)

/// Varredura diagnóstica antes do chamado "Sem internet": consulta status
/// (ONU online) + aparelhos (total + selo de saúde) via GenieACS e mostra
/// pro cliente com orientação por cenário. Nunca bloqueia: erro/timeout/
/// sem ONU → onConcluir(null) (segue pro formulário sem diagnóstico).
class TriagemRede extends ConsumerStatefulWidget {
  const TriagemRede({
    super.key,
    required this.onConcluir,
    required this.onResolveu,
  });

  /// Cliente quer seguir com o chamado. diagnostico == null → varredura
  /// não rolou (bypass).
  final ValueChanged<Map<String, dynamic>?> onConcluir;

  /// Cliente desistiu do chamado ("Resolveu, valeu!").
  final VoidCallback onResolveu;

  @override
  ConsumerState<TriagemRede> createState() => _TriagemRedeState();
}

enum _Fase { escaneando, resultado }

class _TriagemRedeState extends ConsumerState<TriagemRede>
    with SingleTickerProviderStateMixin {
  _Fase _fase = _Fase.escaneando;
  bool? _online;
  int? _totalAparelhos;
  List<String> _nomesAparelhos = const [];
  String _saude = 'indisponivel';
  Map<String, dynamic>? _diagnostico;

  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat();

  @override
  void initState() {
    super.initState();
    _varrer();
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _varrer() async {
    try {
      final results = await Future.wait([
        // métodos reais do repository (Step 1):
        // ref.read(redeRepositoryProvider).status(),
        // ref.read(redeRepositoryProvider).aparelhos(),
      ]).timeout(const Duration(seconds: 12));
      // extrair: online (status), total/saude/nomes (aparelhos)
      // se encontrada == false em qualquer um → bypass
      // montar _diagnostico = {
      //   'online': _online,
      //   'total_aparelhos': _totalAparelhos,
      //   'saude': _saude,
      //   'timestamp': DateTime.now().toUtc().toIso8601String(),
      // }
      if (!mounted) return;
      setState(() => _fase = _Fase.resultado);
    } on Object {
      // Timeout/erro/sem ONU → segue pro formulário sem bloquear.
      if (!mounted) return;
      widget.onConcluir(null);
    }
  }

  // build: fase escaneando → radar pulsante (3 círculos concêntricos com
  // AnimatedBuilder no _pulse, cores BrandTokens.primary com alphas
  // decrescentes) + "Verificando sua conexão…" + subtítulo do passo atual.
  // fase resultado → cards (_CardOnu, _CardAparelhos expansível, _CardSinal)
  // + _Orientacao(cenário) + Row de botões:
  //   OutlinedButton "Resolveu, valeu!" → widget.onResolveu()
  //   FilledButton "Ainda preciso de ajuda" → widget.onConcluir(_diagnostico)
}
```

**Cenários da orientação (widget `_Orientacao`):**
- `_saude == 'fraca' || _online == false` → ícone warning, "Encontramos um problema do nosso lado" + "O sinal da tua fibra está fraco — isso explica a lentidão. Abre o chamado que a gente resolve." (tom: já assume responsabilidade)
- `_totalAparelhos != null && _totalAparelhos! >= 10` → "Tem bastante gente na rede" + "São $_totalAparelhos aparelhos conectados — em horário de pico isso pesa. Desconectar alguns pode resolver."
- caso contrário → "Tua conexão parece saudável" + "Sinal ótimo e ONU online. Reiniciar o roteador (tira da tomada 10s) resolve a maioria dos casos."

O código completo dos cards/orientação fica a cargo do implementador seguindo o design system (BrandTokens, EmptyState/ErrorCard como referência de estilo, selo de saúde igual ao da tela `/rede` — olhe `rede_screen.dart` pra copiar o visual do selo).

- [ ] **Step 3: Integrar no wizard**

Em `novo_chamado_screen.dart`:
- Estado novo: `bool _triagemPendente = false;` e `Map<String, dynamic>? _diagnostico;`
- No Step 0, ao escolher tipo: se `tipo == 'sem_internet'` → `setState { _tipo = t; _triagemPendente = true; }` (NÃO avança `_step`). Outros tipos: comportamento atual.
- No build: se `_triagemPendente` → renderiza `TriagemRede(onConcluir: (diag) => setState { _diagnostico = diag; _triagemPendente = false; _step = 1; }, onResolveu: () => Navigator/context.pop())` no lugar do conteúdo do step.
- No `_enviar` (POST): adicionar ao payload:
```dart
    if (_diagnostico != null) {
      payload['diagnostico'] = _diagnostico;
    }
```
- Voltar do step 1 pro 0 reseta `_diagnostico = null` (se o usuário trocar de tipo).

- [ ] **Step 4: Verificar e commitar**

Run: `flutter analyze && flutter test`
Expected: limpo / PASS.

```bash
git add lib/features/suporte
git commit -m "feat(app/suporte): triagem com varredura GenieACS antes do chamado sem internet"
```

### Task 3: Bloco "Diagnóstico na abertura" na dashboard de OS

**Files:**
- Modify: `apps/dashboard/app/(admin)/cliente-app-os/page.tsx`

- [ ] **Step 1: Renderizar o diagnóstico**

Hoje o payload aparece como JSON cru na Section "Dados adicionais" (linhas ~423-429). Mudar:

```tsx
{o.payload.diagnostico != null && (
  <Section title="Diagnóstico na abertura">
    <div className="grid gap-2 sm:grid-cols-3 text-sm">
      <div className="rounded-md border bg-zinc-50 p-3">
        <div className="text-xs text-muted-foreground">ONU</div>
        <div className="font-semibold">
          {(o.payload.diagnostico as Record<string, unknown>).online ? 'Online' : 'Offline'}
        </div>
      </div>
      <div className="rounded-md border bg-zinc-50 p-3">
        <div className="text-xs text-muted-foreground">Aparelhos conectados</div>
        <div className="font-semibold">
          {String((o.payload.diagnostico as Record<string, unknown>).total_aparelhos ?? '—')}
        </div>
      </div>
      <div className="rounded-md border bg-zinc-50 p-3">
        <div className="text-xs text-muted-foreground">Sinal</div>
        <div className="font-semibold capitalize">
          {String((o.payload.diagnostico as Record<string, unknown>).saude ?? '—')}
        </div>
      </div>
    </div>
    <p className="mt-1 text-xs text-muted-foreground">
      Capturado no momento da abertura
      {(o.payload.diagnostico as Record<string, unknown>).timestamp
        ? ` — ${new Date(String((o.payload.diagnostico as Record<string, unknown>).timestamp)).toLocaleString('pt-BR')}`
        : ''}
    </p>
  </Section>
)}
```

(Ajustar tipagem ao padrão real do arquivo — se `o.payload` for `Record<string, unknown>` tipado, extrair `const diag = o.payload.diagnostico as {online?: boolean; total_aparelhos?: number; saude?: string; timestamp?: string} | undefined` no topo do componente pra não repetir casts.)

Na Section "Dados adicionais" existente: filtrar a chave `diagnostico` do JSON cru (`Object.fromEntries(Object.entries(o.payload).filter(([k]) => k !== 'diagnostico'))`) e só renderizar a section se sobrar chave.

- [ ] **Step 2: Verificar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla/apps/dashboard && npx next build`
Expected: verde.

```bash
git add 'app/(admin)/cliente-app-os/page.tsx'
git commit -m "feat(dashboard/os): bloco Diagnostico na abertura (triagem do app)"
```

---

## FATIA 3 — Chat in-app com consultar_rede_app

### Task 4: Tool loop no endpoint do chat

**Files:**
- Modify: `apps/api/src/ondeline_api/api/v1/cliente_app_chat.py`

- [ ] **Step 1: Conferir os tipos do adapter LLM**

Ler `apps/api/src/ondeline_api/adapters/llm/base.py` (ou onde `ChatRequest`/`ChatMessage`/`Role`/`ToolSpec`/`ToolCall` vivem — grep `class ToolSpec`). O Hermes já serializa `tools` (via `to_openai_schema()`) e parseia `tool_calls`. Anotar o construtor exato do `ToolSpec`.

- [ ] **Step 2: Tool + loop**

Em `cliente_app_chat.py`:

1. **System prompt**: adicionar ao bloco "O que voce pode fazer":
```
- Consultar a rede do cliente em tempo real (aparelhos conectados e qualidade
  do sinal da fibra) — use a tool consultar_rede_app quando ele reclamar de
  internet lenta, caindo ou instavel. Traduza o resultado pra linguagem
  simples: sinal "fraca" = problema na fibra do nosso lado (oriente abrir
  chamado na aba Suporte); muitos aparelhos = rede congestionada; tudo ok =
  sugira reiniciar o roteador.
```
E REMOVER do "O que voce NAO faz" a parte de "Acessar dados especificos do cliente" referente a rede (manter pra plano/fatura).

2. **Tool spec + executor** (módulo-level no arquivo):

```python
_CONSULTAR_REDE_SPEC = ToolSpec(
    name="consultar_rede_app",
    description=(
        "Consulta a rede do cliente logado: quantos aparelhos estao conectados "
        "agora, se a ONU esta online e a qualidade do sinal da fibra. Use quando "
        "o cliente reclamar de internet lenta, caindo ou instavel."
    ),
    parameters={"type": "object", "properties": {}},
)


async def _exec_consultar_rede(
    session: AsyncSession, user: ClienteAppUser
) -> dict[str, Any]:
    """Versao app da tool consultar_rede: CPF vem do user autenticado."""
    cpf = decrypt_pii(user.cpf_encrypted) if user.cpf_encrypted else ""
    if not cpf:
        return {"encontrada": False, "motivo": "cpf_indisponivel"}
    genie = GenieAcsClient(base_url=get_settings().genieacs_url)
    rede = RedeService(session=session, genieacs=genie, sgp_cache=SgpCacheRepo(session))
    try:
        diag = await rede.diagnostico_rede(cpf)
        if not diag.encontrada or diag.device is None:
            return {"encontrada": False, "motivo": diag.motivo}
        d = diag.device
        rx = d.sinal.rx_power if d.sinal else None
        label, emoji = qualidade_sinal(rx)
        return {
            "encontrada": True,
            "online": d.online,
            "aparelhos_conectados": len(d.aparelhos),
            "sinal": {"qualidade": label, "emoji": emoji},
        }
    except GenieAcsUnavailableError:
        return {"erro": "indisponivel"}
    finally:
        await genie.aclose()
```

(⚠️ conferir como `RedeService` é construído no endpoint `cliente_app_rede.py` — copiar o MESMO jeito, incluindo `sgp_cache`. Conferir import real de `SgpCacheRepo`/equivalente lá.)

3. **Loop no `send`** (substituindo a chamada única ao provider):

```python
    messages = [system_msg, *history_msgs, user_msg]
    total_tokens = 0
    bot_text: str | None = None
    for _ in range(3):  # max 3 iteracoes (1 tool + resposta na pratica)
        resp = await provider.chat(
            ChatRequest(
                model=settings.llm_model,
                messages=messages,
                tools=[_CONSULTAR_REDE_SPEC],
                temperature=0.5,
            )
        )
        total_tokens += resp.tokens_used
        if resp.tool_calls:
            messages.append(
                ChatMessage(
                    role=Role.ASSISTANT, content=None, tool_calls=list(resp.tool_calls)
                )
            )
            for tc in resp.tool_calls:
                if tc.name == "consultar_rede_app":
                    result = await _exec_consultar_rede(session, user)
                else:
                    result = {"erro": "tool_desconhecida"}
                messages.append(
                    ChatMessage(
                        role=Role.TOOL,
                        content=json.dumps(result, ensure_ascii=False),
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )
            continue
        bot_text = resp.content
        break
    if not bot_text:
        bot_text = (
            "Nao consegui completar a consulta agora. Tenta de novo em instantes?"
        )
```

(Adaptar nomes de variáveis ao código real do `send` — temperatura, modelo e montagem de histórico já existem lá; preservar gravação criptografada + `llm_tokens_used=total_tokens`.)

- [ ] **Step 3: Validar e commitar**

Run: `cd /Users/robertalbino/Developer/blabla && uvx ruff check apps/api/src && (cd apps/api && .venv/bin/mypy src/ondeline_api/api/v1/cliente_app_chat.py)`
Expected: limpo.

```bash
git add apps/api/src/ondeline_api/api/v1/cliente_app_chat.py
git commit -m "feat(chat-app): tool consultar_rede_app — bot do app consulta rede via GenieACS"
```

### Task 5: Testes do tool loop

**Files:**
- Create ou Modify: `apps/api/tests/test_cliente_app_chat_tools.py` (se já existir teste do chat, estender o arquivo existente — grep `cliente_app_chat` em tests/)

- [ ] **Step 1: Escrever os testes**

Padrão de fixtures dos testes cliente-app existentes (token via `jwt_mod.encode_cliente_access_token`). Mockar o provider LLM (monkeypatch de onde o `send` obtém o HermesProvider) e o `RedeService.diagnostico_rede`:

1. `test_chat_sem_tool`: provider fake responde direto com texto (sem tool_calls) → resposta salva, role bot.
2. `test_chat_com_consultar_rede`: provider fake responde 1º turno com `tool_calls=[ToolCall(id='t1', name='consultar_rede_app', arguments={})]` e 2º turno com texto final; `diagnostico_rede` mockado retornando device com 5 aparelhos e sinal ok → asserts: resposta final salva, RedeService chamado 1x, mensagem TOOL passou no histórico do 2º turno (inspecionar as chamadas do provider fake).
3. `test_chat_genieacs_indisponivel`: `diagnostico_rede` levanta `GenieAcsUnavailableError` → bot ainda responde (resultado da tool = `{"erro": "indisponivel"}`), turno não explode.

- [ ] **Step 2: Validar e commitar**

Run: `uvx ruff check apps/api/tests && (cd apps/api && .venv/bin/mypy src/ondeline_api/api/v1/cliente_app_chat.py)`
Expected: limpo. (pytest roda no CI.)

```bash
git add apps/api/tests
git commit -m "test(chat-app): cobre tool loop do consultar_rede_app (com/sem tool, GenieACS fora)"
```

---

### Task 6: Verificação final

- [ ] `flutter analyze && flutter test` (app) limpo/PASS.
- [ ] `uvx ruff check apps/api/src apps/api/tests` + mypy nos arquivos tocados limpos.
- [ ] `npx next build` (dashboard) verde.
- [ ] Smoke conceitual: nomes de campos do diagnóstico batem app ↔ dashboard (`online`, `total_aparelhos`, `saude`, `timestamp`); tool name `consultar_rede_app` consistente; system prompt não promete o que a tool não faz.
- [ ] Aguardar OK do Robert pra push.
