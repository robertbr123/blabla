# Cliente App — Fase 7: Polimento + LGPD + stores

> subagent-driven. Checkbox `- [ ]`.

**Goal:** Tirar do app a fricção pra publicação. LGPD ok, polimento de UX, instruções de build.

**Entregavel:**
1. Backend: `DELETE /api/v1/cliente-app/me` — anonimiza e marca inativo (LGPD)
2. Backend: testes
3. Flutter: telas estáticas de Termos de Uso + Política de Privacidade (conteúdo placeholder, Robert customiza)
4. Flutter: link "Excluir minha conta" no Perfil (com confirmação dupla)
5. Flutter: haptic feedback nas ações chave (copiar PIX, abrir chamado, login OK)
6. Flutter: link pra termos na tela de "Criar senha" (LGPD exige consentimento informado)
7. Docs: checklist de build release Android + iOS + ícone + screenshots

## Decisões

- **Anonimização ≠ delete físico.** O registro fica em `cliente_app_users` mas com nome/tel/email/cpf zerados, `status='deleted'`. Histórico de OS preservado (foreign key intacta) — admin/legal pode precisar. CPF substituído por placeholder UUID-like pra liberar o índice unique.
- **Termos/privacidade**: Markdown estático no app (sem chamada API). Conteúdo placeholder — Robert troca antes de publicar.
- **Build release**: não rodo aqui. Documento o checklist completo.
- **Ícones**: gerar com `flutter_launcher_icons` package — instruções no checklist.
