/// Validador de CPF (digitos verificadores) e CNPJ.
/// Aceita string com pontuacao — extrai digitos antes.

String onlyDigits(String s) => s.replaceAll(RegExp(r'\D'), '');

bool isValidCpf(String input) {
  final cpf = onlyDigits(input);
  if (cpf.length != 11) return false;
  // Rejeita 11111111111, 22222222222, etc.
  if (RegExp(r'^(\d)\1{10}$').hasMatch(cpf)) return false;

  int sum = 0;
  for (int i = 0; i < 9; i++) {
    sum += int.parse(cpf[i]) * (10 - i);
  }
  int dv1 = (sum * 10) % 11;
  if (dv1 == 10) dv1 = 0;
  if (dv1 != int.parse(cpf[9])) return false;

  sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += int.parse(cpf[i]) * (11 - i);
  }
  int dv2 = (sum * 10) % 11;
  if (dv2 == 10) dv2 = 0;
  return dv2 == int.parse(cpf[10]);
}

bool isValidCnpj(String input) {
  final cnpj = onlyDigits(input);
  if (cnpj.length != 14) return false;
  if (RegExp(r'^(\d)\1{13}$').hasMatch(cnpj)) return false;

  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  int sum = 0;
  for (int i = 0; i < 12; i++) {
    sum += int.parse(cnpj[i]) * w1[i];
  }
  int dv1 = sum % 11;
  dv1 = dv1 < 2 ? 0 : 11 - dv1;
  if (dv1 != int.parse(cnpj[12])) return false;

  sum = 0;
  for (int i = 0; i < 13; i++) {
    sum += int.parse(cnpj[i]) * w2[i];
  }
  int dv2 = sum % 11;
  dv2 = dv2 < 2 ? 0 : 11 - dv2;
  return dv2 == int.parse(cnpj[13]);
}

bool isValidCpfOrCnpj(String input) {
  final d = onlyDigits(input);
  if (d.length == 11) return isValidCpf(d);
  if (d.length == 14) return isValidCnpj(d);
  return false;
}

String formatCpf(String cpf) {
  final d = onlyDigits(cpf);
  if (d.length != 11) return cpf;
  return '${d.substring(0, 3)}.${d.substring(3, 6)}.${d.substring(6, 9)}-${d.substring(9)}';
}

String formatCep(String cep) {
  final d = onlyDigits(cep);
  if (d.length != 8) return cep;
  return '${d.substring(0, 5)}-${d.substring(5)}';
}

String formatPhone(String s) {
  final d = onlyDigits(s);
  if (d.length == 11) {
    return '(${d.substring(0, 2)}) ${d.substring(2, 7)}-${d.substring(7)}';
  }
  if (d.length == 10) {
    return '(${d.substring(0, 2)}) ${d.substring(2, 6)}-${d.substring(6)}';
  }
  return s;
}
