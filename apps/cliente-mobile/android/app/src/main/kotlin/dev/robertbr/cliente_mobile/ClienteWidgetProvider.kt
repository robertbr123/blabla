package dev.robertbr.cliente_mobile

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PorterDuff
import android.graphics.PorterDuffColorFilter
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetBackgroundIntent
import es.antonborri.home_widget.HomeWidgetLaunchIntent
import es.antonborri.home_widget.HomeWidgetProvider

/**
 * Widget de home screen do cliente.
 *
 * Mostra:
 * - Bolinha + texto curto de status de conexão (ativo / suspenso / cancelado)
 * - Valor da próxima fatura
 * - Vencimento legível
 *
 * Dados são salvos pelo Flutter via [es.antonborri.home_widget.HomeWidgetPlugin]
 * (SharedPreferences chave "HomeWidgetPreferences"). O update vem do AppWidget
 * framework (period em widget_info.xml) ou de uma chamada explícita do app.
 */
class ClienteWidgetProvider : HomeWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
        widgetData: android.content.SharedPreferences,
    ) {
        appWidgetIds.forEach { widgetId ->
            val views = RemoteViews(context.packageName, R.layout.cliente_widget)

            val statusRaw = widgetData.getString("status_conexao", null) ?: "desconhecido"
            val (statusLabel, statusColor) = when (statusRaw) {
                "ativo" -> Pair("Online", Color.parseColor("#14B8B0"))
                "suspenso" -> Pair("Suspenso", Color.parseColor("#E8A33D"))
                "cancelado" -> Pair("Cancelado", Color.parseColor("#E0455A"))
                else -> Pair("Conexão", Color.parseColor("#9FB3D9"))
            }
            views.setTextViewText(R.id.widget_status_text, statusLabel)
            views.setInt(
                R.id.widget_status_dot,
                "setColorFilter",
                statusColor,
            )

            val valor = widgetData.getString("proxima_fatura_valor", null)
            val vencimento = widgetData.getString("proxima_fatura_vencimento", null)
            if (valor.isNullOrEmpty()) {
                views.setTextViewText(R.id.widget_valor, "—")
                views.setTextViewText(R.id.widget_vencimento, "Abra o app pra ver")
            } else {
                views.setTextViewText(R.id.widget_valor, valor)
                views.setTextViewText(
                    R.id.widget_vencimento,
                    vencimento ?: "Vencimento indisponível",
                )
            }

            // Tap no widget abre o app na tela de faturas.
            val pendingIntent: PendingIntent = HomeWidgetLaunchIntent.getActivity(
                context,
                MainActivity::class.java,
                android.net.Uri.parse("clientemobile://widget/faturas"),
            )
            views.setOnClickPendingIntent(android.R.id.background, pendingIntent)

            appWidgetManager.updateAppWidget(widgetId, views)
        }
    }
}
