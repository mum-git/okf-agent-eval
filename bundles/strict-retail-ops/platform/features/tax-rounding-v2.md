---
id: platform.feature.tax_rounding_v2
type: feature
title: Tax rounding v2
owner: checkout-platform
rollout_id: ff-2026-06-tax-rounding-v2
status: active
tags:
  - feature-flag
  - distractor
---
# Tax Rounding v2

Tax rounding v2 changed checkout display rounding for taxes. It did not write
to `margin_daily`, did not use the order line ledger, and was not the cause of
the June 12, 2026 net margin anomaly.

