---
id: commerce.metric.net_margin
type: metric
title: "Net margin"
owner: knowledge-team
grain: day-region-channel
source_dataset: commerce.dataset.margin_daily
primary_key: "metric_date, region, channel"
metadata_profile: uniform-heavy
task_hint: "margin anomaly synthesis"
tags:
  - margin
  - anomaly-investigation
domain: commerce
area: metrics
depth: 2
---
# Net Margin

Net margin is calculated as recognized revenue minus cost of goods, shipping
subsidies, payment fees, refunds, and promotional adjustments.

For June 2026 investigations, the authoritative daily table is
`margin_daily`. Promotional adjustments must be deduplicated at
`order_line_id` before they contribute to net margin.

