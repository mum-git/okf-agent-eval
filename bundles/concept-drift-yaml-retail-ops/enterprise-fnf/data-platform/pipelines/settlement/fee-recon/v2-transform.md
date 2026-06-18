---
id: fnf.pipeline.settlement_fee_revenue_v2
type: pipeline_transform
title: settlement_fee_revenue_v2
owner: concept-knowledge-team
schedule: daily
target_asset: fnf.dw.finance.view.settlement_fee_revenue_daily
bad_join_key: loan_number
correct_join_key: closing_id
tags:
  - enterprise-fnf
  - pipeline
  - california
  - root-cause
domain: data-platform
area: fee-recon
depth: 5
metadata_profile: concept-drift-enterprise
task_hint: "california fnf national title refinance fee revenue settlement"
---
# settlement_fee_revenue_v2

`settlement_fee_revenue_v2` builds `finance.settlement_fee_revenue_daily` from
`settlement.closing_order_fact` and fee schedule tables.

The September 2026 deploy introduced a join on `loan_number` instead of
`closing_id`. Because `loan_number` is not unique at closing grain — a
refinance on the same property can carry the same loan number across multiple
order rows — fee revenue rows were de-duplicated incorrectly, understating
California refinance fee revenue for FNF National Title.

The correct join key is `closing_id`.
