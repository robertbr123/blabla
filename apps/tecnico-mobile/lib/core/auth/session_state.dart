class SessionSnapshot {
  final String userId;
  final String role;
  final String nome;
  final bool biometricEnabled;

  const SessionSnapshot({
    required this.userId,
    required this.role,
    required this.nome,
    required this.biometricEnabled,
  });
}
