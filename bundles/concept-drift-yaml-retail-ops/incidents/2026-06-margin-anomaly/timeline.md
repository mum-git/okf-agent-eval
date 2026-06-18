---
id: incident.2026_06_margin_anomaly.timeline
type: incident_timeline
title: "June 2026 margin anomaly timeline"
incident_id: inc-2026-06-margin-anomaly
owner: concept-knowledge-team
metadata_profile: concept-drift-enterprise
task_hint: "margin anomaly synthesis"
tags:
  - incident
  - net-margin
domain: incidents
area: margin-anomaly
depth: 3
---
# Timeline

At 10:20 ET, Finance Analytics detected a 7.8 point drop in net margin for the
Northeast web channel. The first alert fired after the 10:00 margin rollup.

At 11:10 ET, the investigation ruled out tax rounding and shipping adjustment
changes because neither wrote to `margin_daily`.

