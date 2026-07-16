import 'dart:async';
import 'dart:math';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// Erro tipado lançado quando qualquer etapa do speedtest falha
/// (rede indisponível, timeout, cancelamento, resposta inesperada).
class SpeedtestFalhou implements Exception {
  SpeedtestFalhou(this.message, [this.cause]);

  final String message;
  final Object? cause;

  @override
  String toString() => 'SpeedtestFalhou: $message';
}

/// Resultado final do teste completo.
class SpeedtestResultado {
  const SpeedtestResultado({
    required this.pingMs,
    required this.downloadMbps,
    required this.uploadMbps,
  });

  final double pingMs;
  final double downloadMbps;
  final double uploadMbps;
}

/// Converte bytes transferidos + tempo decorrido em Mbps (megabit por segundo).
///
/// bytes * 8 = bits; bits / 1e6 = megabits; megabits / segundos = Mbps.
/// Retorna 0 quando a duração é zero/negativa ou não há bytes, evitando
/// divisão por zero ou infinito durante janelas de medição muito curtas.
double mbpsFrom(int bytes, Duration elapsed) {
  final seconds = elapsed.inMicroseconds / Duration.microsecondsPerSecond;
  if (seconds <= 0 || bytes <= 0) return 0;
  final bits = bytes * 8;
  return (bits / 1e6) / seconds;
}

/// Mediana de uma lista de amostras (ex.: tempos de ping em ms).
/// Lista vazia retorna 0. Não modifica a lista de entrada.
double medianMs(List<double> samples) {
  if (samples.isEmpty) return 0;
  final sorted = List<double>.from(samples)..sort();
  final n = sorted.length;
  final mid = n ~/ 2;
  if (n.isOdd) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

/// Engine do speedtest in-app medindo contra a Cloudflare
/// (https://speed.cloudflare.com), independente do dio principal do app
/// (sem baseUrl/interceptor de auth — é tráfego público de terceiro).
class SpeedtestService {
  SpeedtestService()
      : _dio = Dio(BaseOptions(
          connectTimeout: const Duration(seconds: 10),
        ));

  final Dio _dio;
  CancelToken? _cancelToken;

  static const _pingUrl = 'https://speed.cloudflare.com/__down?bytes=0';
  static const _downloadUrl =
      'https://speed.cloudflare.com/__down?bytes=25000000';
  static const _uploadUrl = 'https://speed.cloudflare.com/__up';
  static const _uploadBytes = 10 * 1000 * 1000; // 10MB
  static const _uploadChunkSize = 64 * 1024; // 64KB por chunk
  static const _windowMs = 500;
  static const _stageTimeout = Duration(seconds: 30);

  /// Cancela qualquer requisição em andamento (chamado, por ex., no
  /// dispose do widget que iniciou o teste).
  void cancel() {
    _cancelToken?.cancel('cancelado pelo usuário');
  }

  /// Libera o dio interno. Chamar quando o dono do serviço for descartado
  /// (ex.: dispose do widget). Após close(), o serviço não deve ser reusado.
  void close() {
    cancel();
    _dio.close(force: true);
  }

  CancelToken _newToken() {
    final token = CancelToken();
    _cancelToken = token;
    return token;
  }

  /// Teto rígido de 30s por etapa: se estourar, cancela a requisição em voo
  /// e converte em [SpeedtestFalhou] com mensagem da etapa.
  Future<T> _withStageTimeout<T>(
    Future<T> future,
    CancelToken token,
    String timeoutMessage,
  ) {
    return future.timeout(_stageTimeout, onTimeout: () {
      token.cancel('timeout da etapa');
      throw SpeedtestFalhou(timeoutMessage);
    });
  }

  /// 5x HEAD no endpoint de 0 bytes da Cloudflare, descarta a 1ª amostra
  /// (aquecimento de conexão TLS) e retorna a mediana das demais em ms.
  /// Teto de 30s pra etapa inteira.
  Future<double> ping() {
    final token = _newToken();
    return _withStageTimeout(
      _ping(token),
      token,
      'O teste de ping demorou demais.',
    );
  }

  Future<double> _ping(CancelToken token) async {
    final amostras = <double>[];
    try {
      for (var i = 0; i < 5; i++) {
        final start = DateTime.now();
        await _dio.head<void>(
          _pingUrl,
          cancelToken: token,
          options: Options(
            receiveTimeout: const Duration(seconds: 10),
            sendTimeout: const Duration(seconds: 10),
          ),
        );
        final elapsed = DateTime.now().difference(start);
        amostras.add(elapsed.inMicroseconds / 1000);
      }
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) rethrow;
      throw SpeedtestFalhou('Não foi possível medir o ping.', e);
    }
    // descarta a 1ª (aquecimento)
    final validas = amostras.length > 1 ? amostras.sublist(1) : amostras;
    return medianMs(validas);
  }

  /// GET em stream de 25MB da Cloudflare; a cada ~500ms reporta a
  /// velocidade instantânea via [onProgress]; retorna a média geral em Mbps.
  /// Teto rígido de 30s pra etapa inteira.
  Future<double> download(void Function(double mbps) onProgress) {
    final token = _newToken();
    return _withStageTimeout(
      _download(token, onProgress),
      token,
      'O teste de download demorou demais.',
    );
  }

  Future<double> _download(
    CancelToken token,
    void Function(double mbps) onProgress,
  ) async {
    final overallStart = DateTime.now();
    var totalBytes = 0;
    var windowBytes = 0;
    var windowStart = DateTime.now();
    try {
      final response = await _dio.get<ResponseBody>(
        _downloadUrl,
        cancelToken: token,
        options: Options(
          responseType: ResponseType.stream,
          receiveTimeout: const Duration(seconds: 30),
          sendTimeout: const Duration(seconds: 30),
        ),
      );
      final stream = response.data?.stream;
      if (stream == null) {
        throw SpeedtestFalhou('Resposta de download vazia da Cloudflare.');
      }
      final completer = Completer<void>();
      late final StreamSubscription<List<int>> sub;
      sub = stream.listen(
        (chunk) {
          totalBytes += chunk.length;
          windowBytes += chunk.length;
          final now = DateTime.now();
          final windowElapsed = now.difference(windowStart);
          if (windowElapsed.inMilliseconds >= _windowMs) {
            onProgress(mbpsFrom(windowBytes, windowElapsed));
            windowBytes = 0;
            windowStart = now;
          }
        },
        onDone: () {
          if (!completer.isCompleted) completer.complete();
        },
        onError: (Object e, StackTrace st) {
          if (!completer.isCompleted) completer.completeError(e, st);
        },
        cancelOnError: true,
      );
      await completer.future;
      await sub.cancel();
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) rethrow;
      throw SpeedtestFalhou('Não foi possível medir o download.', e);
    } catch (e) {
      if (e is SpeedtestFalhou) rethrow;
      throw SpeedtestFalhou('Não foi possível medir o download.', e);
    }
    final overallElapsed = DateTime.now().difference(overallStart);
    return mbpsFrom(totalBytes, overallElapsed);
  }

  /// POST de um corpo de 10MB pseudo-aleatório à Cloudflare (gerado em
  /// chunks Uint8List de 64KB, sem alocar o corpo inteiro em memória);
  /// reporta janelas de progresso via [onProgress] usando o onSendProgress
  /// do dio; retorna a média geral em Mbps. Teto rígido de 30s pra etapa.
  Future<double> upload(void Function(double mbps) onProgress) {
    final token = _newToken();
    return _withStageTimeout(
      _upload(token, onProgress),
      token,
      'O teste de upload demorou demais.',
    );
  }

  Future<double> _upload(
    CancelToken token,
    void Function(double mbps) onProgress,
  ) async {
    final overallStart = DateTime.now();
    var lastSent = 0;
    var windowStart = DateTime.now();
    try {
      await _dio.post<void>(
        _uploadUrl,
        data: _bodyChunks(_uploadBytes),
        cancelToken: token,
        options: Options(
          contentType: 'application/octet-stream',
          headers: {Headers.contentLengthHeader: _uploadBytes},
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 30),
        ),
        onSendProgress: (sent, total) {
          final now = DateTime.now();
          final windowElapsed = now.difference(windowStart);
          final windowBytes = sent - lastSent;
          if (windowElapsed.inMilliseconds >= _windowMs && windowBytes > 0) {
            onProgress(mbpsFrom(windowBytes, windowElapsed));
            lastSent = sent;
            windowStart = now;
          }
        },
      );
    } on DioException catch (e) {
      if (CancelToken.isCancel(e)) rethrow;
      throw SpeedtestFalhou('Não foi possível medir o upload.', e);
    } catch (e) {
      if (e is SpeedtestFalhou) rethrow;
      throw SpeedtestFalhou('Não foi possível medir o upload.', e);
    }
    final overallElapsed = DateTime.now().difference(overallStart);
    return mbpsFrom(_uploadBytes, overallElapsed);
  }

  /// Gera o corpo do upload preguiçosamente: um único chunk de 64KB
  /// pseudo-aleatório é preenchido uma vez e reemitido até somar [total]
  /// bytes (mesmo propósito de entropia — payload não compressível trivial —
  /// sem custo por chunk nem 10MB residentes em memória).
  Stream<Uint8List> _bodyChunks(int total) async* {
    final rnd = Random();
    final chunk = Uint8List(_uploadChunkSize);
    for (var i = 0; i < chunk.length; i++) {
      chunk[i] = rnd.nextInt(256);
    }
    var emitted = 0;
    while (emitted < total) {
      final restante = total - emitted;
      if (restante >= chunk.length) {
        yield chunk;
        emitted += chunk.length;
      } else {
        yield Uint8List.sublistView(chunk, 0, restante);
        emitted = total;
      }
    }
  }
}
