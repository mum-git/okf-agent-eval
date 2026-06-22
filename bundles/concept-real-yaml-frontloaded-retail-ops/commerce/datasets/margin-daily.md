---
id: commerce.dataset.margin_daily
type: dataset
title: Margin daily
owner: finance-analytics
grain: metric_date, region, channel
primary_key: metric_date, region, channel
metadata_profile: uniform-heavy
tags:
  - margin
  - daily-rollup
---
# Margin Daily

`margin_daily` rolls order-line revenue and costs into daily margin metrics.
The June 12, 2026 backfill consumed promotional adjustments from the pricing
shadow ledger.

