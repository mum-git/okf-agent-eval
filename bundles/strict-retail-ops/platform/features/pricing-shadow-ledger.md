---
id: platform.feature.pricing_shadow_ledger
type: feature
title: Pricing shadow ledger
owner: pricing-platform
rollout_id: ff-2026-06-pricing-shadow-ledger
status: rolled-back
enabled_at: "2026-06-12T09:15:00-04:00"
disabled_at: "2026-06-12T13:05:00-04:00"
tags:
  - feature-flag
  - anomaly-root-cause
---
# Pricing Shadow Ledger

The pricing shadow ledger replayed promotional adjustments before the canonical
pricing ledger switched over. Its June 12 rollout was controlled by
`ff-2026-06-pricing-shadow-ledger`.

The faulty transform joined adjustment rows to order lines by `sku` instead of
`order_line_id`, duplicating promotional adjustments for shared SKUs.

