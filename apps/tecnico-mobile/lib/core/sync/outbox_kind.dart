enum OutboxKind {
  iniciar,
  concluir,
  foto,
}

extension OutboxKindString on OutboxKind {
  String get wire => name;
  static OutboxKind parse(String s) => OutboxKind.values.firstWhere(
        (k) => k.name == s,
        orElse: () => OutboxKind.iniciar,
      );
}
