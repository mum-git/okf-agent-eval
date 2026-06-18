---
id: deep.pipeline.wallet_eligibility_cache
type: pipeline
title: Wallet eligibility cache
owner: loyalty-platform
cache_name: wallet_eligibility_cache
expected_key: customer_profile_id
bad_key: household_id
tags:
  - deep-benchmark
  - pipeline
---
# Wallet Eligibility Cache

`wallet_eligibility_cache` should be keyed by `customer_profile_id`.

During the loyalty wallet accelerator variant B rollout, the cache reused
`household_id` across linked profiles. That caused eligible Pacific gold
loyalty mobile-web profiles to be marked ineligible before checkout.

