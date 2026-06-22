---
id: deep.incident.2026_08_pacific_loyalty_drop.root_cause
type: root_cause
title: Pacific loyalty conversion drop root cause
incident_id: inc-2026-08-pacific-loyalty-drop
affected_metric: deep.metric.pacific.mobile_checkout_conversion
affected_segment: pacific gold loyalty mobile web
experiment_id: exp-2026-q3-loyalty-wallet-accelerator
bad_identity_key: household_id
correct_identity_key: customer_profile_id
tags:
  - deep-benchmark
  - root-cause
---
# Root Cause

The August 4, 2026 Pacific loyalty conversion drop was caused by the loyalty
wallet eligibility cache reusing `household_id` across linked profiles.

Variant B of `exp-2026-q3-loyalty-wallet-accelerator` wrote eligibility under
`household_id` instead of `customer_profile_id`. The cache then marked eligible
gold loyalty mobile-web profiles ineligible, reducing mobile checkout
conversion.

