---
id: commerce.dataset.order_line_ledger
type: dataset
title: Order line ledger
owner: commerce-data
grain: order_line_id
primary_key: order_line_id
metadata_profile: uniform-heavy
task_hint: margin anomaly synthesis
tags:
  - order-lines
  - join-keys
---
# Order Line Ledger

The order line ledger is the source of truth for item-level commerce events.
Every row is uniquely identified by `order_line_id`.

`sku` is not unique in this table. Joining adjustments by `sku` duplicates
adjustments across every line that shares the same item identifier.

