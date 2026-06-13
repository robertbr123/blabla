import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/chat_repository.dart';
import '../../core/api/dto.dart';
import '../../core/branding/brand_tokens.dart';
import 'widgets/chat_bubble.dart';

class ChatTab extends ConsumerStatefulWidget {
  const ChatTab({super.key, this.topPadding = 0});

  final double topPadding;

  @override
  ConsumerState<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends ConsumerState<ChatTab> {
  final _scroll = ScrollController();
  final _input = TextEditingController();
  final _focus = FocusNode();
  final List<ChatMessageDto> _msgs = [];
  bool _loading = true;
  bool _sending = false;
  Timer? _poller;
  DateTime? _lastSeen;

  @override
  void initState() {
    super.initState();
    _bootstrap();
    _poller = Timer.periodic(const Duration(seconds: 5), (_) => _poll());
  }

  @override
  void dispose() {
    _poller?.cancel();
    _scroll.dispose();
    _input.dispose();
    _focus.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    try {
      final list = await ref.read(chatRepositoryProvider).list();
      if (!mounted) return;
      setState(() {
        _msgs
          ..clear()
          ..addAll(list);
        if (list.isNotEmpty) _lastSeen = list.last.createdAt;
        _loading = false;
      });
      _jumpToEnd();
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _poll() async {
    if (!mounted || _sending) return;
    try {
      final list = await ref.read(chatRepositoryProvider).list(limit: 20);
      if (!mounted) return;
      // Filtra apenas mensagens novas vs _lastSeen
      final novas = _lastSeen == null
          ? list
          : list.where((m) => m.createdAt.isAfter(_lastSeen!)).toList();
      if (novas.isEmpty) return;
      setState(() {
        _msgs.addAll(novas);
        _lastSeen = _msgs.last.createdAt;
      });
      _jumpToEnd();
    } catch (_) {
      // silencioso — proximo poll tenta de novo
    }
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _sending) return;
    _input.clear();
    // Otimismo: adiciona msg do user na lista antes da resposta
    final tempUser = ChatMessageDto(
      id: 'temp-${DateTime.now().microsecondsSinceEpoch}',
      role: 'user',
      content: text,
      createdAt: DateTime.now().toUtc(),
    );
    setState(() {
      _msgs.add(tempUser);
      _sending = true;
    });
    _jumpToEnd();

    try {
      final r = await ref.read(chatRepositoryProvider).send(text);
      if (!mounted) return;
      setState(() {
        // Substitui temp user msg pela real + adiciona resposta bot
        _msgs.removeWhere((m) => m.id == tempUser.id);
        _msgs.add(r.user);
        _msgs.add(r.bot);
        _lastSeen = r.bot.createdAt;
        _sending = false;
      });
      _jumpToEnd();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _msgs.removeWhere((m) => m.id == tempUser.id);
        _sending = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Falha ao enviar. Tente de novo.')),
      );
    }
  }

  void _jumpToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _msgs.isEmpty && !_sending
                  ? _Welcome(
                      onTapExample: _useExample,
                      topPadding: widget.topPadding,
                    )
                  : ListView.builder(
                      controller: _scroll,
                      padding: EdgeInsets.only(
                        top: widget.topPadding + BrandTokens.spaceMd,
                        bottom: BrandTokens.spaceMd,
                      ),
                      itemCount: _msgs.length + (_sending ? 1 : 0),
                      itemBuilder: (_, i) {
                        if (i == _msgs.length && _sending) {
                          return const TypingBubble();
                        }
                        return ChatBubble(msg: _msgs[i]);
                      },
                    ),
        ),
        SafeArea(
          top: false,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: BrandTokens.spaceMd,
              vertical: BrandTokens.spaceSm,
            ),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              border: Border(
                top: BorderSide(color: BrandTokens.divider.withOpacity(0.5)),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    focusNode: _focus,
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.newline,
                    decoration: const InputDecoration(
                      hintText: 'Escreva uma mensagem...',
                      border: InputBorder.none,
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: BrandTokens.spaceSm),
                Material(
                  color: BrandTokens.primary,
                  shape: const CircleBorder(),
                  child: InkWell(
                    customBorder: const CircleBorder(),
                    onTap: _sending ? null : _send,
                    child: SizedBox(
                      width: 44,
                      height: 44,
                      child: _sending
                          ? const Padding(
                              padding: EdgeInsets.all(10),
                              child: CircularProgressIndicator(
                                strokeWidth: 2.4,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.send, color: Colors.white, size: 20),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  void _useExample(String s) {
    _input.text = s;
    _focus.requestFocus();
  }
}

class _Welcome extends StatelessWidget {
  const _Welcome({required this.onTapExample, this.topPadding = 0});
  final void Function(String) onTapExample;
  final double topPadding;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.only(
        top: topPadding + BrandTokens.spaceXl,
        left: BrandTokens.spaceXl,
        right: BrandTokens.spaceXl,
        bottom: BrandTokens.spaceXl,
      ),
      children: [
        const SizedBox(height: BrandTokens.spaceXl),
        Center(
          child: Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: BrandTokens.primary.withOpacity(0.10),
              borderRadius: BorderRadius.circular(BrandTokens.radiusXl),
            ),
            child: const Icon(Icons.chat_bubble_outline,
                color: BrandTokens.primary, size: 32),
          ),
        ),
        const SizedBox(height: BrandTokens.spaceLg),
        Text(
          'Como posso ajudar?',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceSm),
        Text(
          'Comece uma conversa. O bot responde em segundos.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: BrandTokens.textSecondary,
              ),
        ),
        const SizedBox(height: BrandTokens.spaceXl),
        for (final s in const [
          'Como funciona o app?',
          'Minha internet ta lenta, o que fazer?',
          'Quero falar com um atendente',
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: BrandTokens.spaceSm),
            child: OutlinedButton(
              onPressed: () => onTapExample(s),
              child: Align(alignment: Alignment.centerLeft, child: Text(s)),
            ),
          ),
      ],
    );
  }
}
