import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'dto.dart';

class ChatSendResult {
  ChatSendResult({required this.user, required this.bot});
  final ChatMessageDto user;
  final ChatMessageDto bot;
}

class ChatRepository {
  ChatRepository(this._dio);
  final Dio _dio;
  static const _base = '/api/v1/cliente-app/chat';

  /// Retorna msgs em ordem cronologica (mais antiga primeiro).
  Future<List<ChatMessageDto>> list({String? cursor, int limit = 50}) async {
    final r = await _dio.get(
      '$_base/messages',
      queryParameters: {
        'limit': limit,
        if (cursor != null) 'cursor': cursor,
      },
    );
    final items = ((r.data as Map)['items'] as List? ?? const [])
        .map((j) => ChatMessageDto.fromJson(j as Map<String, dynamic>))
        .toList();
    // API devolve DESC; UI prefere ASC pra exibir top-bottom
    return items.reversed.toList();
  }

  Future<ChatSendResult> send(String text) async {
    final r = await _dio.post('$_base/send', data: {'text': text});
    final data = r.data as Map<String, dynamic>;
    return ChatSendResult(
      user: ChatMessageDto.fromJson(data['user_message'] as Map<String, dynamic>),
      bot: ChatMessageDto.fromJson(data['bot_message'] as Map<String, dynamic>),
    );
  }
}

final chatRepositoryProvider = Provider<ChatRepository>(
  (ref) => ChatRepository(ref.watch(apiClientProvider)),
);
