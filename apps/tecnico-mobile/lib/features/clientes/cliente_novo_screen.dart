import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/location/location_service.dart';
import '../../core/ui/app_section_header.dart';
import '../../core/ui/app_status_chip.dart';
import '../../core/ui/app_surfaces.dart';
import '../../core/util/cpf_validator.dart';
import '../../core/util/viacep.dart';
import '../estoque/estoque_data.dart';
import 'cliente_data.dart';
import 'cliente_form_data.dart';

class ClienteNovoScreen extends ConsumerStatefulWidget {
  const ClienteNovoScreen({super.key});

  @override
  ConsumerState<ClienteNovoScreen> createState() => _ClienteNovoScreenState();
}

class _ClienteNovoScreenState extends ConsumerState<ClienteNovoScreen> {
  int _step = 0;

  // Step 1 — dados pessoais
  final _cpf = TextEditingController();
  final _nome = TextEditingController();
  DateTime? _dob;
  final _telefone = TextEditingController();
  final _email = TextEditingController();

  // Step 2 — endereço + plano
  final _cep = TextEditingController();
  final _address = TextEditingController();
  final _number = TextEditingController();
  final _complement = TextEditingController();
  final _neighborhood = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController();
  SgpPlano? _planoSelecionado;
  final _pppoeUser = TextEditingController();
  final _pppoePass = TextEditingController();
  int _dueDate = 10;

  // Step 3 — instalação
  final _serial = TextEditingController();
  final _contrato = TextEditingController();
  final _observation = TextEditingController();
  final Map<String, int> _materiaisQtd = {}; // itemId -> qtd
  final Map<String, String> _materiaisSerial =
      {}; // itemId -> serial (serializado)

  // GPS background
  LocationResult? _gps;
  bool _gpsCapturing = false;

  // CEP busca
  Timer? _cepDebounce;
  bool _cepBuscando = false;

  // Submit
  bool _enviando = false;
  String? _erroEnvio;

  @override
  void initState() {
    super.initState();
    // Captura GPS em background ao abrir
    _capturarGps();
  }

  @override
  void dispose() {
    _cpf.dispose();
    _nome.dispose();
    _telefone.dispose();
    _email.dispose();
    _cep.dispose();
    _address.dispose();
    _number.dispose();
    _complement.dispose();
    _neighborhood.dispose();
    _city.dispose();
    _state.dispose();
    _pppoeUser.dispose();
    _pppoePass.dispose();
    _serial.dispose();
    _contrato.dispose();
    _observation.dispose();
    _cepDebounce?.cancel();
    super.dispose();
  }

  Future<void> _capturarGps() async {
    setState(() => _gpsCapturing = true);
    final loc = await ref.read(locationServiceProvider).capture();
    if (!mounted) return;
    setState(() {
      _gps = loc;
      _gpsCapturing = false;
    });
  }

  void _onCepChanged(String v) {
    _cepDebounce?.cancel();
    if (onlyDigits(v).length < 8) return;
    _cepDebounce = Timer(const Duration(milliseconds: 400), _buscarCep);
  }

  Future<void> _buscarCep() async {
    setState(() => _cepBuscando = true);
    final endereco = await buscarCep(_cep.text);
    if (!mounted) return;
    setState(() => _cepBuscando = false);
    if (endereco == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('CEP não encontrado.')),
      );
      return;
    }
    _address.text = endereco.logradouro;
    _neighborhood.text = endereco.bairro;
    _city.text = endereco.localidade;
    _state.text = endereco.uf;
  }

  // ── Validações por step ─────────────────────────────────────

  String? _validaStep1() {
    if (!isValidCpfOrCnpj(_cpf.text)) return 'CPF/CNPJ inválido.';
    if (_nome.text.trim().isEmpty) return 'Nome é obrigatório.';
    if (_dob == null) return 'Data de nascimento é obrigatória.';
    final tel = onlyDigits(_telefone.text);
    if (tel.length < 10) return 'Telefone inválido (mínimo 10 dígitos).';
    final email = _email.text.trim();
    if (email.isNotEmpty &&
        !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      return 'Email inválido.';
    }
    return null;
  }

  String? _validaStep2() {
    if (_address.text.trim().isEmpty) return 'Endereço é obrigatório.';
    if (_number.text.trim().isEmpty) return 'Número é obrigatório.';
    if (_city.text.trim().isEmpty) return 'Cidade é obrigatória.';
    if (_planoSelecionado == null) return 'Selecione um plano.';
    if (![10, 20, 30].contains(_dueDate)) {
      return 'Vencimento deve ser dia 10, 20 ou 30.';
    }
    return null;
  }

  // Step 3 não tem validação obrigatória — tudo opcional.

  Future<void> _enviar() async {
    setState(() {
      _enviando = true;
      _erroEnvio = null;
    });
    try {
      final materiais = _materiaisQtd.entries
          .where((e) => e.value > 0)
          .map(
            (e) => CreateClienteCampoMaterial(
              itemId: e.key,
              quantidade: e.value,
              serial: _materiaisSerial[e.key],
            ),
          )
          .toList();

      final body = CreateClienteCampoIn(
        cpf: onlyDigits(_cpf.text),
        nome: _nome.text.trim(),
        dob: DateFormat('yyyy-MM-dd').format(_dob!),
        telefone: onlyDigits(_telefone.text),
        email: _email.text.trim().isEmpty ? null : _email.text.trim(),
        cep: _cep.text.trim().isEmpty ? null : onlyDigits(_cep.text),
        address: _address.text.trim(),
        number: _number.text.trim(),
        complement:
            _complement.text.trim().isEmpty ? null : _complement.text.trim(),
        neighborhood: _neighborhood.text.trim().isEmpty
            ? null
            : _neighborhood.text.trim(),
        city: _city.text.trim(),
        state: _state.text.trim().isEmpty
            ? null
            : _state.text.trim().toUpperCase(),
        planId: _planoSelecionado?.isFallback == true
            ? null
            : _planoSelecionado?.id,
        planNome: _planoSelecionado!.descricao,
        pppoeUser:
            _pppoeUser.text.trim().isEmpty ? null : _pppoeUser.text.trim(),
        pppoePass: _pppoePass.text.isEmpty ? null : _pppoePass.text,
        dueDate: _dueDate,
        serial: _serial.text.trim().isEmpty ? null : _serial.text.trim(),
        contrato: _contrato.text.trim().isEmpty ? null : _contrato.text.trim(),
        observation:
            _observation.text.trim().isEmpty ? null : _observation.text.trim(),
        latitude: _gps?.lat,
        longitude: _gps?.lng,
        locationAccuracy: _gps?.accuracyMeters,
        materiais: materiais,
      );

      final actions = ref.read(clienteFormActionsProvider);
      final id = await actions.criar(body);
      if (!mounted) return;
      // Invalida lista pra refletir o novo cliente
      ref.invalidate(clientesListProvider);
      // Vai pro detalhe SUBSTITUINDO a tela de cadastro (nao `go`, que apagaria
      // a pilha e deixaria o detail sem botao de voltar -> usuario preso).
      context.pushReplacement('/clientes/$id');
    } on DioException catch (e) {
      final body = e.response?.data;
      final detail = body is Map ? body['detail']?.toString() : null;
      setState(
        () => _erroEnvio = detail ?? e.message ?? 'Erro ao cadastrar.',
      );
    } catch (e) {
      setState(() => _erroEnvio = e.toString());
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surfaceContainerLowest,
      appBar: AppBar(
        title: const Text('Novo cliente'),
        actions: [
          // Status do GPS no header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Center(child: _GpsChip(gps: _gps, capturing: _gpsCapturing)),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
              child: AppSurfaceCard(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const AppSectionHeader(
                            title: 'Cadastro guiado',
                            subtitle:
                                'Organize os dados pessoais, a conexão e a instalação em 3 etapas objetivas.',
                          ),
                          const SizedBox(height: 14),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              AppStatusChip(
                                label: 'Etapa ${_step + 1} de 3',
                                tone: AppStatusTone.info,
                              ),
                              AppStatusChip(
                                label: _gpsCapturing
                                    ? 'GPS em segundo plano'
                                    : _gps == null
                                        ? 'GPS indisponível'
                                        : 'GPS capturado',
                                tone: _gpsCapturing
                                    ? AppStatusTone.info
                                    : _gps == null
                                        ? AppStatusTone.warning
                                        : AppStatusTone.success,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: scheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Center(
                        child: _GpsChip(
                          gps: _gps,
                          capturing: _gpsCapturing,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: AppSurfaceCard(
                  padding: EdgeInsets.zero,
                  child: Theme(
                    data: Theme.of(context).copyWith(
                      dividerColor: Colors.transparent,
                    ),
                    child: Stepper(
                      physics: const ClampingScrollPhysics(),
                      margin: EdgeInsets.zero,
                      currentStep: _step,
                      onStepTapped: (i) {
                        if (i < _step) setState(() => _step = i);
                      },
                      controlsBuilder: (ctx, details) {
                        return Padding(
                          padding: const EdgeInsets.only(top: 16),
                          child: Row(
                            children: [
                              if (_step > 0) ...[
                                Expanded(
                                  child: OutlinedButton(
                                    onPressed: () => setState(() => _step -= 1),
                                    child: const Text('Voltar'),
                                  ),
                                ),
                                const SizedBox(width: 8),
                              ],
                              if (_step < 2)
                                Expanded(
                                  flex: 2,
                                  child: FilledButton(
                                    onPressed: () {
                                      final erro = _step == 0
                                          ? _validaStep1()
                                          : _validaStep2();
                                      if (erro != null) {
                                        ScaffoldMessenger.of(context)
                                            .showSnackBar(
                                          SnackBar(content: Text(erro)),
                                        );
                                        return;
                                      }
                                      setState(() => _step += 1);
                                    },
                                    child: const Text('Continuar'),
                                  ),
                                ),
                              if (_step == 2)
                                Expanded(
                                  flex: 2,
                                  child: FilledButton.icon(
                                    icon: const Icon(Icons.check),
                                    onPressed: _enviando ? null : _enviar,
                                    label: Text(
                                      _enviando
                                          ? 'Salvando…'
                                          : 'Salvar cliente',
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        );
                      },
                      steps: [
                        _stepDados(),
                        _stepEnderecoPlano(),
                        _stepInstalacao(),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Step _stepDados() {
    final cpfValido = _cpf.text.isEmpty || isValidCpfOrCnpj(_cpf.text);
    return Step(
      title: const Text('Dados'),
      isActive: _step >= 0,
      state: _step > 0 ? StepState.complete : StepState.indexed,
      content: _StepPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _cpf,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: 'CPF / CNPJ',
                prefixIcon: const Icon(Icons.credit_card),
                suffixIcon: _cpf.text.isEmpty
                    ? null
                    : Icon(
                        cpfValido ? Icons.check_circle : Icons.error,
                        color: cpfValido ? Colors.green : Colors.red,
                      ),
                errorText: cpfValido ? null : 'Dígitos verificadores inválidos',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nome,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                labelText: 'Nome completo',
                prefixIcon: Icon(Icons.person_outline),
              ),
            ),
            const SizedBox(height: 12),
            InkWell(
              onTap: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: _dob ?? DateTime(1990, 1, 1),
                  firstDate: DateTime(1900),
                  lastDate: DateTime.now(),
                );
                if (picked != null) setState(() => _dob = picked);
              },
              child: InputDecorator(
                decoration: const InputDecoration(
                  labelText: 'Data de nascimento',
                  prefixIcon: Icon(Icons.cake_outlined),
                ),
                child: Text(
                  _dob != null
                      ? DateFormat('dd/MM/yyyy').format(_dob!)
                      : 'Selecione…',
                  style: TextStyle(
                    color: _dob != null
                        ? null
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _telefone,
              keyboardType: TextInputType.phone,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(11),
              ],
              decoration: const InputDecoration(
                labelText: 'Telefone (com DDD)',
                prefixIcon: Icon(Icons.phone_iphone),
                hintText: 'Ex: 92999998888',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Email (opcional)',
                prefixIcon: Icon(Icons.email_outlined),
                hintText: 'cliente@exemplo.com',
              ),
            ),
          ],
        ),
      ),
    );
  }

  Step _stepEnderecoPlano() {
    return Step(
      title: const Text('Endereço & Plano'),
      isActive: _step >= 1,
      state: _step > 1 ? StepState.complete : StepState.indexed,
      content: _StepPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _cep,
              keyboardType: TextInputType.number,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(8),
              ],
              onChanged: _onCepChanged,
              decoration: InputDecoration(
                labelText: 'CEP',
                prefixIcon: const Icon(Icons.markunread_mailbox_outlined),
                suffixIcon: _cepBuscando
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    : null,
                helperText: 'Autocompleta endereço',
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextField(
                    controller: _address,
                    textCapitalization: TextCapitalization.words,
                    decoration: const InputDecoration(
                      labelText: 'Endereço',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 1,
                  child: TextField(
                    controller: _number,
                    keyboardType: TextInputType.text,
                    decoration: const InputDecoration(labelText: 'N°'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _complement,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Complemento (opcional)',
                hintText: 'Apto, bloco…',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _neighborhood,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Bairro'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextField(
                    controller: _city,
                    textCapitalization: TextCapitalization.words,
                    decoration: const InputDecoration(labelText: 'Cidade'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 1,
                  child: TextField(
                    controller: _state,
                    textCapitalization: TextCapitalization.characters,
                    inputFormatters: [LengthLimitingTextInputFormatter(2)],
                    decoration: const InputDecoration(labelText: 'UF'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _PlanoSelector(
              selecionado: _planoSelecionado,
              onSelect: (p) => setState(() {
                _planoSelecionado = p;
              }),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _pppoeUser,
                    decoration: const InputDecoration(
                      labelText: 'PPPoE login',
                      prefixIcon: Icon(Icons.key),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _pppoePass,
                    decoration: const InputDecoration(
                      labelText: 'PPPoE senha',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(Icons.calendar_today, size: 18),
                const SizedBox(width: 8),
                const Text('Vencimento'),
                const SizedBox(width: 8),
                Expanded(
                  child: Wrap(
                    spacing: 8,
                    children: [10, 20, 30]
                        .map(
                          (day) => ChoiceChip(
                            label: Text('Dia $day'),
                            selected: _dueDate == day,
                            onSelected: (_) => setState(() => _dueDate = day),
                          ),
                        )
                        .toList(),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Step _stepInstalacao() {
    return Step(
      title: const Text('Instalação'),
      isActive: _step >= 2,
      content: _StepPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // GPS status
            _GpsCard(
                gps: _gps, capturing: _gpsCapturing, onRetry: _capturarGps),
            const SizedBox(height: 12),
            TextField(
              controller: _serial,
              decoration: const InputDecoration(
                labelText: 'Serial do equipamento (ONU)',
                prefixIcon: Icon(Icons.qr_code_2),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _contrato,
              decoration: const InputDecoration(
                labelText: 'Contrato (opcional)',
                prefixIcon: Icon(Icons.description_outlined),
              ),
            ),
            const SizedBox(height: 12),
            _MateriaisSelector(
              qtdPorItem: _materiaisQtd,
              serialPorItem: _materiaisSerial,
              onChange: () => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _observation,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Observação (opcional)',
              ),
            ),
            if (_erroEnvio != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Theme.of(context)
                      .colorScheme
                      .errorContainer
                      .withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.error_outline,
                        size: 18, color: Theme.of(context).colorScheme.error),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _erroEnvio!,
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 8),
            const Text(
              'Após salvar, você poderá anexar fotos da instalação.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Widgets de apoio ────────────────────────────────────────

class _GpsChip extends StatelessWidget {
  final LocationResult? gps;
  final bool capturing;
  const _GpsChip({this.gps, required this.capturing});

  @override
  Widget build(BuildContext context) {
    if (capturing) {
      return const Padding(
        padding: EdgeInsets.all(8),
        child: SizedBox(
          height: 14,
          width: 14,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    }
    if (gps == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(horizontal: 8),
        child: Icon(Icons.location_off, size: 18, color: Colors.orange),
      );
    }
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 8),
      child: Icon(Icons.location_on, size: 18, color: Colors.green),
    );
  }
}

class _StepPanel extends StatelessWidget {
  final Widget child;

  const _StepPanel({required this.child});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(22),
      ),
      child: child,
    );
  }
}

class _GpsCard extends StatelessWidget {
  final LocationResult? gps;
  final bool capturing;
  final VoidCallback onRetry;
  const _GpsCard({
    required this.gps,
    required this.capturing,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final ok = gps != null && !capturing;
    final color = ok ? const Color(0xFF16a34a) : const Color(0xFFf59e0b);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          if (capturing)
            const SizedBox(
              height: 18,
              width: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            Icon(ok ? Icons.location_on : Icons.location_off, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  ok
                      ? 'GPS capturado'
                      : capturing
                          ? 'Capturando GPS…'
                          : 'GPS não disponível',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: scheme.onSurface,
                  ),
                ),
                if (ok)
                  Text(
                    '${gps!.lat.toStringAsFixed(6)}, ${gps!.lng.toStringAsFixed(6)} (±${gps!.accuracyMeters?.toStringAsFixed(0) ?? "?"}m)',
                    style: TextStyle(
                      fontSize: 11,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
          ),
          if (!ok && !capturing)
            TextButton(onPressed: onRetry, child: const Text('Tentar')),
        ],
      ),
    );
  }
}

class _PlanoSelector extends ConsumerWidget {
  final SgpPlano? selecionado;
  final ValueChanged<SgpPlano> onSelect;
  const _PlanoSelector({required this.selecionado, required this.onSelect});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(planosProvider);
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: scheme.outlineVariant),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.wifi, size: 18),
              const SizedBox(width: 8),
              const Text('Plano *',
                  style: TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.refresh, size: 16),
                onPressed: () => ref.invalidate(planosProvider),
                tooltip: 'Atualizar do SGP',
              ),
            ],
          ),
          async.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(12),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => Padding(
              padding: const EdgeInsets.all(8),
              child: Text(
                'Erro ao buscar planos do SGP: $e',
                style: TextStyle(color: scheme.error, fontSize: 12),
              ),
            ),
            data: (planos) {
              if (planos.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(8),
                  child: Text('Nenhum plano disponível no SGP.'),
                );
              }
              return DropdownButton<int>(
                isExpanded: true,
                value: selecionado?.id,
                hint: const Text('Selecione um plano…'),
                items: planos
                    .map(
                      (p) => DropdownMenuItem<int>(
                        value: p.id,
                        child: Text(
                          '${p.descricao} · ${p.velocidadeStr()} · R\$ ${p.preco.toStringAsFixed(2)}',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
                onChanged: (id) {
                  final p = planos.firstWhere((x) => x.id == id);
                  onSelect(p);
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

class _MateriaisSelector extends ConsumerWidget {
  final Map<String, int> qtdPorItem;
  final Map<String, String> serialPorItem;
  final VoidCallback onChange;

  const _MateriaisSelector({
    required this.qtdPorItem,
    required this.serialPorItem,
    required this.onChange,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(estoqueSaldoProvider);
    final scheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: scheme.outlineVariant),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            Icon(Icons.inventory_2_outlined, size: 18),
            SizedBox(width: 8),
            Text('Materiais usados',
                style: TextStyle(fontWeight: FontWeight.w700)),
          ]),
          Text(
            'Baixa do seu estoque ao salvar (atômico).',
            style: TextStyle(
              fontSize: 11,
              color: scheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          async.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(12),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => Padding(
              padding: const EdgeInsets.all(8),
              child: Text(
                'Erro ao carregar estoque: $e',
                style: TextStyle(color: scheme.error, fontSize: 12),
              ),
            ),
            data: (linhas) {
              final disponiveis = linhas.where((l) => l.saldo > 0).toList();
              if (disponiveis.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(8),
                  child: Text('Você não tem material em estoque.'),
                );
              }
              return Column(
                children: disponiveis.map((l) {
                  final qtd = qtdPorItem[l.itemId] ?? 0;
                  return _MaterialRow(
                    linha: l,
                    quantidade: qtd,
                    serial: serialPorItem[l.itemId] ?? '',
                    onQtdChanged: (v) {
                      if (v <= 0) {
                        qtdPorItem.remove(l.itemId);
                        if (l.serializado) serialPorItem.remove(l.itemId);
                      } else {
                        qtdPorItem[l.itemId] = v;
                      }
                      onChange();
                    },
                    onSerialChanged: (s) {
                      if (s.trim().isEmpty) {
                        serialPorItem.remove(l.itemId);
                      } else {
                        serialPorItem[l.itemId] = s.trim();
                      }
                      onChange();
                    },
                  );
                }).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _MaterialRow extends StatefulWidget {
  final EstoqueLinha linha;
  final int quantidade;
  final String serial;
  final ValueChanged<int> onQtdChanged;
  final ValueChanged<String> onSerialChanged;

  const _MaterialRow({
    required this.linha,
    required this.quantidade,
    required this.serial,
    required this.onQtdChanged,
    required this.onSerialChanged,
  });

  @override
  State<_MaterialRow> createState() => _MaterialRowState();
}

class _MaterialRowState extends State<_MaterialRow> {
  late final TextEditingController _serialCtrl;

  @override
  void initState() {
    super.initState();
    _serialCtrl = TextEditingController(text: widget.serial);
  }

  @override
  void didUpdateWidget(covariant _MaterialRow old) {
    super.didUpdateWidget(old);
    // Sincroniza so se mudou externamente (ex: reset via remove qtd).
    if (widget.serial != _serialCtrl.text && widget.serial.isEmpty) {
      _serialCtrl.text = '';
    }
  }

  @override
  void dispose() {
    _serialCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final linha = widget.linha;
    final selected = widget.quantidade > 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      linha.nome,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      '${linha.sku} · saldo ${linha.saldo}${linha.serializado ? " · serial" : ""}',
                      style: const TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.remove_circle_outline),
                onPressed: widget.quantidade > 0
                    ? () => widget.onQtdChanged(widget.quantidade - 1)
                    : null,
              ),
              Text('${widget.quantidade}',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              IconButton(
                icon: const Icon(Icons.add_circle_outline),
                onPressed: widget.quantidade < linha.saldo &&
                        (!linha.serializado || widget.quantidade < 1)
                    ? () => widget.onQtdChanged(widget.quantidade + 1)
                    : null,
              ),
            ],
          ),
          if (selected && linha.serializado)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: TextField(
                controller: _serialCtrl,
                onChanged: widget.onSerialChanged,
                decoration: const InputDecoration(
                  isDense: true,
                  labelText: 'Serial do item *',
                  prefixIcon: Icon(Icons.qr_code_2, size: 18),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
