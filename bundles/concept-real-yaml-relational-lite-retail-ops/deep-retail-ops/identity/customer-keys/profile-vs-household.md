---
id: deep.identity.profile_vs_household
type: identity_key_reference
title: Customer profile vs household identity keys
owner: identity-platform
canonical_checkout_key: customer_profile_id
non_unique_key: household_id
tags:
  - deep-benchmark
  - identity
---
# Profile vs Household

`customer_profile_id` is the canonical identity key for checkout eligibility,
wallet allocation, and per-profile experiment assignment.

`household_id` groups linked profiles. It must not be used as the wallet
eligibility cache key because it can mark one eligible profile ineligible when
another linked profile consumes or suppresses a wallet credit.

