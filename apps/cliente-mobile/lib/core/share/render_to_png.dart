import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';

/// Renderiza um widget arbitrario num PNG offscreen, sem precisar
/// estar na tree.
///
/// `logicalSize` e o tamanho "design" (px Flutter) do card. `pixelRatio`
/// controla a resolucao final — 3.0 e equivalente a um dispositivo
/// densidade ~xxhdpi (recomendado pra status do WhatsApp).
///
/// Uso tipico: `final bytes = await renderWidgetToPng(myCard, size: Size(360, 640));`
Future<Uint8List> renderWidgetToPng(
  Widget widget, {
  required Size logicalSize,
  double pixelRatio = 3.0,
}) async {
  final repaint = RenderRepaintBoundary();
  final platformDispatcher = WidgetsBinding.instance.platformDispatcher;
  final view = platformDispatcher.views.first;

  final renderView = RenderView(
    view: view,
    configuration: ViewConfiguration(
      logicalConstraints: BoxConstraints.tight(logicalSize),
      physicalConstraints: BoxConstraints.tight(logicalSize * pixelRatio),
      devicePixelRatio: pixelRatio,
    ),
    child: RenderPositionedBox(
      alignment: Alignment.center,
      child: repaint,
    ),
  );

  final pipelineOwner = PipelineOwner()..rootNode = renderView;
  renderView.prepareInitialFrame();

  final buildOwner = BuildOwner(focusManager: FocusManager());
  final rootElement = RenderObjectToWidgetAdapter<RenderBox>(
    container: repaint,
    child: Directionality(
      textDirection: TextDirection.ltr,
      child: MediaQuery(
        data: MediaQueryData(
          devicePixelRatio: pixelRatio,
          size: logicalSize,
          textScaler: TextScaler.noScaling,
        ),
        child: widget,
      ),
    ),
  ).attachToRenderTree(buildOwner);

  buildOwner
    ..buildScope(rootElement)
    ..finalizeTree();
  pipelineOwner
    ..flushLayout()
    ..flushCompositingBits()
    ..flushPaint();

  final ui.Image image = await repaint.toImage(pixelRatio: pixelRatio);
  final ByteData? byteData =
      await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  if (byteData == null) {
    throw StateError('Falha ao serializar PNG.');
  }
  return byteData.buffer.asUint8List();
}
