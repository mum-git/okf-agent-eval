---
id: incident.2026_06_margin_anomaly.root_cause
type: root_cause
title: Root cause for June 2026 margin anomaly
incident_id: inc-2026-06-margin-anomaly
owner: finance-analytics
metadata_profile: uniform-heavy
tags:
  - root-cause
  - anomaly-investigation
---
# Root Cause

The June 12, 2026 net margin drop was caused by the pricing shadow ledger
duplicating promotional adjustments.

The bad transform joined promotional adjustment rows by `sku` instead of
`order_line_id`. Because many order lines share a SKU, the transform multiplied
adjustments before they reached `margin_daily`, reducing reported net margin.

