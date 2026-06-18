---
id: commerce.dataset.margin_daily
type: dataset
title: "Margin daily"
owner: knowledge-team
grain: "metric_date, region, channel"
primary_key: "metric_date, region, channel"
metadata_profile: uniform-heavy
task_hint: "margin anomaly synthesis"
tags:
  - margin
  - daily-rollup
domain: commerce
area: datasets
depth: 2
---
# Margin Daily

`margin_daily` rolls order-line revenue and costs into daily margin metrics.
The June 12, 2026 backfill consumed promotional adjustments from the pricing
shadow ledger.

