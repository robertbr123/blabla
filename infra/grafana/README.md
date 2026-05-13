# Grafana dashboards — Ondeline v2

This directory contains importable Grafana dashboard JSON artifacts for the
Ondeline v2 platform. The dashboards are **not** provisioned automatically — the
M8 scope only ships the JSON; operators import them manually into an existing
Grafana instance.

## Data source

Both dashboards expect a **Prometheus** data source with UID `prometheus`
configured in Grafana. If your Prometheus data source uses a different UID,
either:

- Rename the data source UID to `prometheus` in Grafana, **or**
- Edit the JSON files and replace every `"uid": "prometheus"` with the UID of
  your existing Prometheus data source before importing.

The Ondeline API exposes Prometheus metrics on `GET /metrics` (port `8000` by
default). Add a scrape job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: ondeline-api
    metrics_path: /metrics
    scrape_interval: 15s
    static_configs:
      - targets:
          - api.ondeline:8000
```

Adjust the `targets` host/port to match your deployment (e.g.
`http://api.ondeline:8000/metrics` becomes target `api.ondeline:8000` with the
default HTTP scheme).

## Import instructions

1. Open Grafana in your browser and log in as an editor/admin.
2. Navigate to **Dashboards → New → Import**.
3. Click **Upload JSON file** and select one of the files from
   `infra/grafana/dashboards/`.
4. On the import screen, pick your Prometheus data source when prompted.
5. Click **Import**. Repeat for the second dashboard.

Each dashboard ships with a stable `uid` so re-importing overwrites the previous
revision instead of creating a duplicate.

## Dashboards shipped

| File                                       | UID                    | Title                          | Panels                                                                                                                                                                                                                                                          |
| ------------------------------------------ | ---------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dashboards/ondeline-operational.json`     | `ondeline-operational` | Ondeline — Operational         | 1. Webhooks recebidos (rate, 5min); 2. Webhooks HMAC inválido (rate); 3. Webhooks rate-limited (rate); 4. Mensagens processadas/min; 5. Dedup ratio (5min); 6. Evolution success rate; 7. Process resident memory; 8. Process CPU (rate, 1min) |
| `dashboards/ondeline-product.json`         | `ondeline-product`     | Ondeline — Product (placeholder) | 1. OS criadas/dia (placeholder text panel); 2. Mensagens/min por status                                                                                                                                                                                          |

## Notes

- `ondeline-product.json` is intentionally minimal. The full product KPI set
  (OS criadas/dia, CSAT, FCR, ...) requires a Postgres data source plugin in
  Grafana, which is deferred to post-cutover infrastructure work. Until then,
  consume those KPIs via the REST endpoint `GET /api/v1/metricas`.
- `schemaVersion: 39` targets Grafana 10.x and is forward-compatible with 11.x.
- Panels use the standard 24-column grid; resize freely after import.
