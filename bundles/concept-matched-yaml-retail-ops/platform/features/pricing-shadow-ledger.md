---
id: platform.feature.pricing_shadow_ledger
type: feature
title: "Pricing shadow ledger"
owner: knowledge-team
rollout_id: ff-2026-06-pricing-shadow-ledger
status: rolled-back
metadata_profile: uniform-heavy
task_hint: "margin anomaly synthesis"
tags:
  - feature-flag
  - anomaly-root-cause
domain: platform
area: features
depth: 2
---
# Pricing Shadow Ledger

The pricing shadow ledger replayed promotional adjustments before the canonical
pricing ledger switched over. Its June 12 rollout was controlled by
`ff-2026-06-pricing-shadow-ledger`.

The faulty transform joined adjustment rows to order lines by `sku` instead of
`order_line_id`, duplicating promotional adjustments for shared SKUs.

