# Task: Write evaluation report + preliminary recommendation for gpt-5.4-mini on enterprise-fnf-synthesis

## Background

We ran a benchmark evaluating how well gpt-5.4-mini (via Codex exec) performs on an "enterprise-fnf-synthesis" task — a file-navigation-and-synthesis benchmark where the agent must read through a realistic enterprise documentation bundle, find relevant information, and produce accurate answers with proper citations.

## Test configuration

- **Model:** gpt-5.4-mini via `codex exec`
- **Task:** `tasks/enterprise-fnf-synthesis.json`
- **Iterations:** 30 (plus 1 warmup discarded)
- **Jobs:** 1 (sequential, to avoid interference)
- **Variants shuffled** with seed 42 (to eliminate position bias)
- **Sandbox:** workspace-write with `approval_policy="never"`

## Three prompt variants tested

Each iteration runs all three variants sequentially in shuffled order:

1. **strict** — Most constrained prompting, enforces rigid answer format and citation rules
2. **extended** — More verbose/elaborate prompts, gives the model more guidance and context
3. **uniform-yaml** — Structured YAML-format prompts, consistent schema across all questions

## Raw results (per variant, 30 runs each)

### extended
- Pass rate: 27/27 graded runs (100%)
- Duration: mean 40.9s | median 38.6s | std dev 10.8s | min 29.2s | max 83.6s | p95 49.4s
- Mean/median ratio: 1.059 (near-symmetric, low skew)
- Total score: mean 0.9958 | median 1.0 | min 0.9571
- Citation score: mean 0.9841 | median 1.0
- Trace score: mean 0.9947 | median 1.0
- Tokens: mean 15,238 | median 13,390 | std dev 6,307 | p95 30,813
- Files read: mean 10.0 | median 10.0

### strict
- Pass rate: 28/28 graded runs (100%)
- Duration: mean 40.3s | median 40.2s | std dev 10.5s | min 23.7s | max 62.9s | p95 61.9s
- Mean/median ratio: 1.002 (most symmetric of all three)
- Total score: mean 0.9824 | median 1.0 | min 0.8286
- Citation score: mean 0.9592 | median 1.0
- Trace score: mean 0.9528 | median 1.0
- Tokens: mean 17,473 | median 14,240 | std dev 8,081 | p95 32,143
- Files read: mean 9.2 | median 9.0

### uniform-yaml
- Pass rate: 27/27 graded runs (100%)
- Duration: mean 40.5s | median 35.4s | std dev 15.7s | min 28.0s | max 109.8s | p95 57.9s
- Mean/median ratio: 1.145 (right-skewed, outliers pull mean up)
- Total score: mean 0.9971 | median 1.0 | min 0.9209
- Citation score: mean 0.9894 | median 1.0
- Trace score: mean 0.9959 | median 1.0
- Tokens: mean 14,059 | median 13,251 | std dev 4,936 | p95 20,139
- Files read: mean 10.9 | median 9.0

## Key findings to highlight in the report

1. **All three variants achieved perfect accuracy** when they passed — every correct answer was fully accurate (accuracy score 1.0 across the board). The differences are purely in efficiency, speed, and consistency.

2. **uniform-yaml is the top performer overall** — fastest median speed (35.4s), lowest token usage (14k avg), and highest mean total score (0.997). However, it has the highest variance (std dev 15.7s) with a notable outlier at ~110s.

3. **extended is the most consistent** — tightest distribution (std dev 10.8s), lowest skew (mean/median ratio 1.059). Only ~8% slower and ~8% more tokens than uniform-yaml. Reads the most files thoroughly.

4. **strict is outclassed on this task** — slowest median (40.2s), highest token usage (17.5k, 24% more than uniform-yaml), AND lowest citation/trace scores. The only advantage is the most symmetric distribution, but extended matches predictability while being faster and cheaper.

5. **All variants show excellent cache behavior** — 94-96% cache hit rates after warmup, meaning subsequent runs benefit significantly from token caching.

6. **Zero distractor file reads across all variants** — none of the runs were misled by decoy files in the bundle.

7. **Median scores are identical (1.0) across all three** — typical performance is perfect regardless of variant. Differences appear in tail behavior and resource consumption.

## Composite ranking (accuracy 40%, efficiency 30%, speed 30%)

| Rank | Variant    | Composite | Efficiency | Speed norm |
|------|-----------|-----------|------------|------------|
| 1    | uniform-yaml | 1.0000   | 1.000      | 1.000      |
| 2    | extended     | 0.9523   | 0.923      | 0.918      |
| 3    | strict       | 0.9057   | 0.805      | 0.881      |

## What to produce

### Part 1: Evaluation Report
Write a clear, well-structured report covering:
- Executive summary (2-3 paragraphs)
- Test methodology
- Detailed results per variant (use the data above)
- Comparative analysis highlighting trade-offs between speed, efficiency, and consistency
- The key findings listed above, elaborated with context

### Part 2: Preliminary Recommendation
Provide a preliminary recommendation on which variant to use as default. This should be provisional — acknowledge that the final decision will come after deeper review of individual run data. Structure it as:
- Recommended default (with justification)
- When to consider alternatives (e.g., "use extended if consistency matters more than peak performance")
- Open questions / areas needing further investigation before finalizing

## Data location
Full run data is at: `/home/ben/okf-agent-eval/runs/batch-20260618T110420Z/`
Summary JSON: `/home/ben/okf-agent-eval/runs/batch-20260618T110420Z/summary.json`

## Output
Write the report to: `/home/ben/okf-agent-eval/reports/gpt54-mini-enterprise-fnf-report.md`
