---
id: deep.experiment.loyalty_wallet_accelerator.variant_b
type: experiment_variant
title: "Loyalty wallet accelerator variant B"
experiment_id: exp-2026-q3-loyalty-wallet-accelerator
owner: knowledge-team
allocation_key_expected: customer_profile_id
allocation_key_observed: household_id
status: disabled
tags:
  - deep-benchmark
  - root-cause-candidate
domain: regions
area: loyalty-wallet-accelerator
depth: 8
metadata_profile: uniform-heavy
task_hint: "deep retail loyalty conversion synthesis"
routing_hint: "inspect regional metric, experiment, identity key, wallet pipeline, and incident remediation"
---
# Loyalty Wallet Accelerator Variant B

Variant B accelerated wallet credit presentation for gold loyalty shoppers in
Pacific mobile web checkout.

On August 4, 2026, variant B wrote wallet eligibility using `household_id`
instead of the expected `customer_profile_id`. That mismatched identity key is
the experiment-side trigger for the conversion drop.

