import 'package:flutter/material.dart';

import '../../../core/api/dto.dart';
import '../../../core/branding/brand_tokens.dart';

class ChatBubble extends StatelessWidget {
  const ChatBubble({super.key, required this.msg});
  final ChatMessageDto msg;

  @override
  Widget build(BuildContext context) {
    final isUser = msg.isUser;
    final isAtendente = msg.role == 'atendente';
    final bg = isUser
        ? BrandTokens.primary
        : isAtendente
            ? BrandTokens.primaryDark
            : Theme.of(context).colorScheme.surface;
    final fg = (isUser || isAtendente) ? Colors.white : BrandTokens.textPrimary;
    final align = isUser ? Alignment.centerRight : Alignment.centerLeft;
    final radius = BorderRadius.only(
      topLeft: const Radius.circular(BrandTokens.radiusLg),
      topRight: const Radius.circular(BrandTokens.radiusLg),
      bottomLeft: Radius.circular(isUser ? BrandTokens.radiusLg : 4),
      bottomRight: Radius.circular(isUser ? 4 : BrandTokens.radiusLg),
    );

    return Container(
      alignment: align,
      padding: const EdgeInsets.symmetric(
        vertical: BrandTokens.spaceXs,
        horizontal: BrandTokens.spaceLg,
      ),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        child: Column(
          crossAxisAlignment:
              isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            if (isAtendente)
              Padding(
                padding: const EdgeInsets.only(
                  left: BrandTokens.spaceXs,
                  bottom: 2,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: const [
                    Icon(Icons.support_agent,
                        size: 12, color: BrandTokens.textSecondary),
                    SizedBox(width: 4),
                    Text(
                      'Atendente',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: BrandTokens.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            Container(
              padding: const EdgeInsets.symmetric(
                vertical: BrandTokens.spaceSm + 2,
                horizontal: BrandTokens.spaceMd,
              ),
              decoration: BoxDecoration(
                color: bg,
                borderRadius: radius,
                boxShadow: (isUser || isAtendente) ? null : BrandTokens.shadowCard,
              ),
              child: Text(
                msg.content,
                style: TextStyle(color: fg, height: 1.35),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class TypingBubble extends StatefulWidget {
  const TypingBubble({super.key});

  @override
  State<TypingBubble> createState() => _TypingBubbleState();
}

class _TypingBubbleState extends State<TypingBubble>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.centerLeft,
      padding: const EdgeInsets.symmetric(
        vertical: BrandTokens.spaceXs,
        horizontal: BrandTokens.spaceLg,
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(
          vertical: BrandTokens.spaceSm + 2,
          horizontal: BrandTokens.spaceMd,
        ),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(BrandTokens.radiusLg),
            topRight: Radius.circular(BrandTokens.radiusLg),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(BrandTokens.radiusLg),
          ),
          boxShadow: BrandTokens.shadowCard,
        ),
        child: AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) {
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                final t = (_ctrl.value + i * 0.2) % 1.0;
                final opacity = (t < 0.5 ? t * 2 : (1 - t) * 2).clamp(0.3, 1.0);
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Opacity(
                    opacity: opacity,
                    child: Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: BrandTokens.textSecondary,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              }),
            );
          },
        ),
      ),
    );
  }
}
