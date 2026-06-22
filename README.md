# OKF Agent Evaluation

This is a standalone benchmark for testing whether an agent can navigate and
use an OKF-style knowledge bundle without losing parseability or accuracy.

## Recommended Designs (Based on Testing)

**For index files:** Use body-routed navigation without YAML metadata
(`body-routed-indexes-retail-ops`). Agents navigate equally well with body-text
routing cues; index frontmatter adds no measurable benefit.

**For concept files:** Use minimal frontmatter — identity + required facts only
(`concept-real-yaml-minimal-retail-ops`). Perfect accuracy, fastest performance
(41s median), and lowest token usage (11.5k median). Additional metadata
(relationships, provenance, hints) costs tokens without improving accuracy.

## PostgreSQL Retrieval Layer (Deep-Bundle Findings)

OKF navigation degrades on **deep, decoy-laden bundles**: agents must traverse
many `index.md` hops, and lookalike directories (several different "canary"
areas in one bundle) lead weak navigators to the wrong files. To test a fix, we
added an optional **PostgreSQL retrieval layer** that indexes every Markdown file
as a searchable chunk (frontmatter + body) keyed to its real bundle-relative
path. Agents issue one search and get the answer files directly, then cite the
real paths — postgres accelerates *discovery and parsing*, it does not replace
the OKF source of truth. See `scripts/okf_search.py`, `scripts/build_postgres_index.py`,
and `scripts/pg_common.py` (Postgres runs locally via the `pgserver` pip package
— no sudo, no system service).

We graded three **depth levels** (L1 shallow → L3 ten-hop) on the optimal
`concept-real-yaml-minimal` bundle, across four agent harnesses, in OKF-only mode
vs. postgres mode (3 iterations each).

### Agent Harnesses

A "harness" is the program that drives the model through the task: it sends the
prompt, exposes tools, runs the model's tool calls, and loops until the model
produces an answer. All four read the task prompt on stdin and emit the
submission + trace JSON on stdout (see `agent_runner.py`), but they differ in how
much of the agent loop is theirs vs. ours.

- **`llama_cpp_tool_agent.py` ("llama tool-agent")** — a minimal agent loop we
  own end-to-end. It POSTs to an OpenAI-compatible `/v1/chat/completions`
  endpoint with a `tools` array of function schemas, the model replies with
  `tool_calls`, the harness executes each call and feeds the result back, and the
  loop repeats until the model stops calling tools. **This is the "tool call"
  loop:** the model never touches the filesystem itself — it *requests* an action
  (`read_file` with a path, or `search_bundle` with a query in postgres mode), our
  code runs it, and returns the content as a `tool` message. Every executed call
  is logged to the trace. Because it is just a thin loop over the standard OpenAI
  function-calling wire format, this harness is the closest analog to an
  application calling a **deployed API model** (e.g. Azure OpenAI): retarget it by
  changing the `base_url`, auth header, and deployment/model name — the loop and
  tool schemas are unchanged. The two tools it exposes:
  - `read_file(path)` — return a bundle file's contents (OKF navigation).
  - `search_bundle(query, file_type, required_keys, limit)` — query the postgres
    layer for chunks (added in `llama_cpp_tool_agent_postgres.py`).
- **`codex` / `opencode`** — third-party *coding-agent CLIs* with their own baked-in
  system prompts, sandboxing, and shell-based tools (they `cat`/`grep`/`find`
  files themselves rather than calling a `read_file` tool we defined). We point
  them at the same local model; they self-report which files they read.
- **`haiku` (fresh Claude Code)** — a clean-room Claude Code agent on the haiku
  model (no plugins/skills/project context), driving its own built-in tools.

In short: the llama tool-agent measures *our* agent loop with explicit tools the
model must call; the other three measure how each *product* navigates when handed
the same bundle.

**Accuracy — OKF mode → (postgres mode scored 1.0 in all 12 configs):**

| harness | L1 | L2 | L3 | OKF navigation style |
|---|---|---|---|---|
| codex (local 27B)    | 1.0 | **0.0** | **0.0** | lazy — stops at first "canary" dir |
| opencode (local 27B) | **0.0** | 1.0 | 1.0 | thorough grep, confused by decoys |
| llama tool-agent (27B) | **0.0** | 1.0 | 1.0 | exhaustive (30–43 files), confused by decoys |
| haiku (fresh Claude Code) | 1.0 | 1.0 | 1.0 | strong — never fails OKF |

Pure-OKF navigation failed in **4 of 12** configs; the postgres layer fixed every
one. *Which* configs fail is harness-specific — it depends entirely on the
agent's navigation temperament.

**Speed Δ (postgres vs OKF) — note the depth crossover:**

| harness | L1 | L2 | L3 |
|---|---|---|---|
| codex    | +47% ✗ | −24% ✓ | −9% ✓ |
| opencode | −43% ✓ | −37% ✓ | −66% ✓ |
| llama    | −31% ✓ | −49% ✓ | −70% ✓ |
| haiku    | **+94% ✗** | **−76% ✓** | **−51% ✓** |

**Token Δ (where captured):** codex L2/L3 −57%/−52%; llama L3 **−87%**; haiku
L2/L3 −54%/−52%. Biggest absolute win: llama L3 read **30 files → 4** (−87%).

**Conclusions:**

1. **Postgres is correctness insurance on deep bundles.** It scored 1.0
   everywhere; OKF-only navigation fails on a third of deep/decoy cases.
2. **There is a real depth crossover** (clearest on haiku, which is 1.0 in both
   modes so it isolates the effect): postgres is a **net loss at L1** (+94%
   slower — the task is trivial and the extra search is pure overhead) but a
   **large win at L2/L3** (−51% to −76% speed, ~−53% tokens). Shallow tasks do
   not justify the layer; deep ones strongly do.
3. **Where postgres hurts: shallow + keyword mismatch.** The L1 query is
   auto-derived from the task prompt ("routed canary"), but L1 files never
   contain the word "routed" — so the search adds cost without precision. The
   layer pays off when the task is deep *and* its vocabulary appears in the files.

Reproduce: `./scripts/setup_postgres.sh && .pgvenv/bin/python scripts/build_postgres_index.py`,
then run paired batches with the `run-<harness>-postgres.sh` wrappers and compare
with `scripts/compare_postgres_runs.py`. Full run outputs are under
`runs/cmp2-L*` and `runs/haiku-L*`.

## All Bundle Variants

The benchmark includes multiple equivalent knowledge bundles to test different metadata strategies:

- `bundles/strict-retail-ops`: strict OKF-style layout. Directory `index.md`
  files are navigation pages, and concept frontmatter lives on concept files.
- `bundles/extended-retail-ops`: intentional extension. Directory `index.md`
  files include inherited YAML frontmatter that becomes more specific deeper in
  the tree.
- `bundles/uniform-yaml-retail-ops`: intentional extension. Directory
  `index.md` files and concept files keep a consistent metadata density across
  depth instead of starting lightweight and getting heavier.
- `bundles/concept-matched-yaml-retail-ops`: concept files inherit the nearest
  index metadata exactly, so index YAML and concept YAML line up.
- `bundles/concept-drift-yaml-retail-ops`: same as `concept-matched-yaml`, but
  three inherited concept fields are nudged away from the parent index.
- `bundles/frontloaded-yaml-retail-ops`: inverse extension. Directory `index.md`
  files start denser at the top and get lighter as you descend.
- `bundles/body-routed-indexes-retail-ops`: ⭐ **index reference design** — index
  files carry no YAML; routing cues live in the body with a `## Key entries:`
  section. Achieves 1.0 accuracy and competitive speed/token metrics.
- `bundles/sparse-index-retail-ops`: alternative index design with minimal
  frontmatter; similar accuracy and performance to body-routed.
- `bundles/concept-frontmatter-canary-retail-ops`: canary extension where
  selected answer facts live only in non-index Markdown concept frontmatter.
- `bundles/concept-frontmatter-sparse-retail-ops`: same canary, but the
  answer-bearing concept files use sparse frontmatter.
- `bundles/concept-frontmatter-expanded-retail-ops`: same canary, but the
  answer-bearing concept files use denser inherited/routing frontmatter.
- `bundles/concept-frontmatter-quoted-retail-ops`: same canary, but the
  answer-bearing concept files quote scalar YAML values.
- `bundles/concept-clean-body-retail-ops`: clean comparison with body-routed
  no-YAML indexes and answer facts in ordinary concept Markdown body text.
- `bundles/concept-clean-yaml-sparse-retail-ops`: same clean comparison, but
  answer facts live only in sparse concept YAML frontmatter.
- `bundles/concept-clean-yaml-okf-retail-ops`: same clean comparison, but
  answer facts live only in denser OKF-style concept YAML frontmatter.
- `bundles/concept-real-control-retail-ops`: ~~clean real control where indexes
  are body-routed, target concept Markdown bodies are identical to the YAML
  variants, and answer facts are absent.~~ **Discontinued** — control variant
  was dropped from batch testing after initial runs showed it consistently
  underperformed both YAML variants: accuracy near 0%, ~3× slower (~155s vs
  ~35-52s), and ~4× token usage (~132K vs ~10-34K). The control served its
  purpose: confirming that without answer-bearing frontmatter, the agent cannot
  reliably synthesize the required facts from body text alone. Kept for
  historical reference only.
- `bundles/concept-real-yaml-sparse-retail-ops`: same real bundle, but answer
  facts live only in sparse YAML frontmatter on non-index concept files.
- `bundles/concept-real-yaml-minimal-retail-ops`: ⭐ **optimal concept design**
  — identity fields plus required domain facts only, no task hints, no relationships.
  Achieves perfect accuracy with lowest token usage (11.5k median) and fastest
  speed (41s median) across all variants.
- `bundles/concept-real-yaml-typed-retail-ops`: same real bundle, with normal
  classification metadata such as domain, system, status, and owner. Tested but
  not part of current evaluation focus.
- `bundles/concept-real-yaml-relational-retail-ops`: same real bundle, with
  relationship metadata for related assets, signals, and files. Tested but not part
  of current evaluation focus.
- `bundles/concept-real-yaml-provenance-retail-ops`: same real bundle, with
  provenance and verification metadata. Tested but underperforms minimal variant.
- `bundles/concept-real-yaml-frontloaded-retail-ops`: same real bundle, with
  decisive operational fields placed first in each target concept frontmatter.
  Tested but shows no accuracy improvement over minimal.
- `bundles/concept-real-yaml-provenance-lite-retail-ops`: same real bundle,
  with lean provenance metadata and duplicated provenance noise removed.
  Tested but not part of current evaluation focus.
- `bundles/concept-real-yaml-relational-lite-retail-ops`: same real bundle,
  with only practical file relationship metadata (1.0 accuracy, 42.1s median,
  12.1k tokens). Marginal cost over minimal without accuracy gain.
- `bundles/concept-real-yaml-minimal-linked-retail-ops`: same real bundle,
  with minimal answer-bearing metadata plus only practical file relationship
  metadata (1.0 accuracy, 41.9s median, 12.1k tokens). File links add ~50ms
  with no measurable benefit.
- `bundles/concept-real-yaml-okf-retail-ops`: same real bundle, but answer
  facts live only in denser OKF-style YAML frontmatter on non-index concept
  files. Kept for historical comparison; it includes task/routing hint fields
  and is not part of the applicable metadata-depth matrix.

The task is synthesis-oriented: the agent must combine facts from multiple
linked concepts to explain a fictional retail margin anomaly.

There are two task levels:

- `tasks/synthesis.json`: shallow baseline task over the original retail ops
  corpus.
- `tasks/deep-synthesis.json`: deeper navigation task over `deep-retail-ops`,
  requiring regional metric, experiment, identity-key, pipeline, incident, and
  remediation evidence.
- `tasks/concept-frontmatter-canary.json`: private grading task with expected
  answers and citation requirements for the canary experiment.
- `tasks/concept-frontmatter-canary.public.json`: public (agent-visible) prompt
  for the canary experiment — contains only the prompt and fact keys, no
  accepted answers.

### Canary Tasks

The canary task (`concept-frontmatter-canary`) tests whether agents can extract
structured facts from YAML frontmatter on **non-index concept files**, not just
from directory `index.md` navigation pages. This is the key capability that
distinguishes agents that actually read concept frontmatter from those that only
skim index pages.

**Task prompt:** investigate the "routed metadata canary" incident and report
12 specific facts:

| Fact key | Description |
| --- | --- |
| `incident_id` | The canary incident identifier |
| `affected_kpi` | The KPI that was impacted |
| `affected_days` | The dates the KPI was affected |
| `root_cause` | What caused the anomaly |
| `metadata_source` | The correct metadata source |
| `incorrect_source` | The incorrect source that was used |
| `pipeline` | The pipeline involved |
| `source_asset` | The source asset identifier |
| `remediation` | The fix applied |
| `owner` | The team that owns the fix |
| `signal_family` | The signal family classification |
| `validation_marker` | The validation marker |

**Target concept files** (answer-bearing frontmatter lives here, relative to
the bundle root — same paths in every canary variant bundle):

- `/enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/root-cause.md`
- `/enterprise-fnf/frontmatter-canary/incidents/2026-11-md-frontmatter-canary/remediation.md`
- `/enterprise-fnf/frontmatter-canary/registry/signal-registry.md`

Each canary bundle (`concept-frontmatter-canary-retail-ops`,
`concept-frontmatter-sparse-retail-ops`, `concept-real-yaml-minimal-retail-ops`,
`concept-real-yaml-minimal-linked-retail-ops`, etc.) contains identical file
trees; only the YAML frontmatter styling on those concept files differs between
variants.

**How to run:** use the `.public.json` task as the agent-visible prompt and the
private `concept-frontmatter-canary.json` as the grading reference:

```bash
python3 batch_runner.py \
  --task tasks/concept-frontmatter-canary.public.json \
  --grade-task tasks/concept-frontmatter-canary.json \
  --variants concept-frontmatter-canary concept-frontmatter-sparse concept-frontmatter-expanded concept-frontmatter-quoted \
  --frontmatter-scope concept \
  --iterations 30 \
  --jobs 3 \
  --shuffle-variants \
  --seed 1 \
  --agent-cmd "codex exec --model gpt-5.4 --sandbox workspace-write -c approval_policy=\"never\" --skip-git-repo-check"
```

The `--grade-task` flag tells the runner to use the private task (with accepted
answers and citation expectations) for scoring while the agent only sees the
public prompt. Without `--grade-task`, the runner uses `--task` for both prompt
and grading.

**Bundle variants tested by the canary:**

- `concept-frontmatter-canary`: baseline — answer facts in concept frontmatter
- `concept-frontmatter-sparse`: same facts in sparse frontmatter
- `concept-frontmatter-expanded`: same facts with denser inherited/routing frontmatter
- `concept-frontmatter-quoted`: same facts with quoted YAML scalar values
- `concept-clean-body`: answer facts in body text only (no YAML on concept files)
- `concept-clean-yaml-sparse`: answer facts in sparse concept YAML only
- `concept-clean-yaml-okf`: answer facts in OKF-style dense concept YAML only

The correct answers are in `answers/concept-frontmatter-canary-correct.json`.

### Depth Levels (L1 / L2 / L3)

The canary task above is **L1**. The harness/postgres comparisons grade three
depth levels — the same 12-fact incident-investigation shape, but with the
three answer-bearing files (root-cause, remediation, registry/signal) buried
progressively deeper inside a separate canary region. Each level is its own
task; all three live in the same bundle (e.g. `concept-real-yaml-minimal-retail-ops`,
which is 180 `.md` files / ~69 KB total) alongside lookalike decoy "canary"
directories meant to mislead shallow navigation.

| Level | Task | Canary region | Region size | Deepest answer file |
| --- | --- | --- | --- | --- |
| **L1** | `concept-frontmatter-canary` (routed) | `/enterprise-fnf/frontmatter-canary/` | 7 `.md` files, 4 subdirs, ~2.7 KB | 4 directory hops (`…/2026-11-md-frontmatter-canary/root-cause.md`) |
| **L2** | `deep-canary-l2` (prism) | `/deep-retail-ops/canary-l2/` | 11 `.md` files, 8 subdirs, ~2.9 KB | 6 directory hops (`…/pipelines/commerce/checkout/wallet/canary-remediation.md`) |
| **L3** | `deep-canary-l3` (nexus) | `/deep-retail-ops/nexus-canary/` | 17 `.md` files, 14 subdirs, ~3.7 KB | 9 directory hops (`…/regions/na/pacific/commerce/checkout/experiments/2027-q1/canary-remediation.md`) |

The regions are deliberately small in bytes — the difficulty is **navigation
depth**, not volume. From L1 to L3 the file count and subdir count more than
double and the deepest answer file goes from 4 to 9 directory hops (a 10-segment
path), which is what stresses an agent's ability to follow `index.md` routing
all the way down instead of giving up at a plausible-looking shallow match. Each
level pairs a public prompt (`tasks/<level>.public.json`) with a private grading
spec (`tasks/<level>.json`); run them exactly like the L1 canary above, swapping
the `--task`/`--grade-task` pair.

## Run The Grader

Validate a bundle:

```bash
python3 grader.py --bundle bundles/strict-retail-ops --strict
python3 grader.py --bundle bundles/extended-retail-ops --extension
python3 grader.py --bundle bundles/uniform-yaml-retail-ops --extension
python3 grader.py --bundle bundles/concept-matched-yaml-retail-ops --extension
python3 grader.py --bundle bundles/concept-drift-yaml-retail-ops --extension
python3 grader.py --bundle bundles/frontloaded-yaml-retail-ops --extension
python3 grader.py --bundle bundles/body-routed-indexes-retail-ops --extension
python3 grader.py --bundle bundles/sparse-index-retail-ops --extension
python3 grader.py --bundle bundles/concept-frontmatter-canary-retail-ops --extension
python3 grader.py --bundle bundles/concept-frontmatter-sparse-retail-ops --extension
python3 grader.py --bundle bundles/concept-frontmatter-expanded-retail-ops --extension
python3 grader.py --bundle bundles/concept-frontmatter-quoted-retail-ops --extension
python3 grader.py --bundle bundles/concept-clean-body-retail-ops --extension
python3 grader.py --bundle bundles/concept-clean-yaml-sparse-retail-ops --extension
python3 grader.py --bundle bundles/concept-clean-yaml-okf-retail-ops --extension
python3 grader.py --bundle bundles/concept-real-control-retail-ops --extension
python3 grader.py --bundle bundles/concept-real-yaml-sparse-retail-ops --extension
python3 grader.py --bundle bundles/concept-real-yaml-okf-retail-ops --extension
```

Score a submitted answer:

```bash
python3 grader.py \
  --bundle bundles/strict-retail-ops \
  --task tasks/synthesis.json \
  --submission answers/example-correct.json \
  --strict
```

Score a submitted answer with an agent trace:

```bash
python3 grader.py \
  --bundle bundles/strict-retail-ops \
  --task tasks/synthesis.json \
  --submission answers/example-correct.json \
  --trace traces/example-efficient.json \
  --strict
```

Run an external agent command and grade it:

```bash
python3 agent_runner.py \
  --bundle bundles/strict-retail-ops \
  --task tasks/deep-synthesis.json \
  --variant strict \
  --mode strict \
  --agent-cmd "your-agent-command"
```

`agent_runner.py` sends the benchmark prompt to the command on stdin, records
real wall-clock duration, extracts the submission and trace JSON from stdout,
writes artifacts under `runs/<timestamp>/`, and writes `grade.json`.

Run repeated iterations across variants:

```bash
python3 batch_runner.py \
  --task tasks/enterprise-fnf-synthesis.json \
  --iterations 3 \
  --jobs 2 \
  --agent-cmd "codex exec --model gpt-5.4 --sandbox workspace-write -c approval_policy=\"never\" --skip-git-repo-check"
```

To compare the YAML-placement variants directly, run:

```bash
python3 batch_runner.py \
  --task tasks/enterprise-fnf-synthesis.json \
  --iterations 30 \
  --jobs 3 \
  --variants uniform-yaml concept-matched-yaml concept-drift-yaml \
  --agent-cmd "codex exec --dangerously-bypass-approvals-and-sandbox --model gpt-5.4-mini --skip-git-repo-check"
```

Use `--jobs 1` for one-after-the-other execution, or increase it for concurrent
agent runs. Batch results are written under `runs/batch-*/results.json` and
`runs/batch-*/summary.json`.

To run optional index-field ablations alongside the baseline variants, add one
or more `--ablate-field` flags. The runner will copy each selected bundle,
remove that field from index frontmatter, and report the metric deltas in
`summary.json` under `field_ablation` and `field_usage`.

```bash
python3 batch_runner.py \
  --task tasks/enterprise-fnf-synthesis.json \
  --iterations 3 \
  --jobs 2 \
  --ablate-field task_hint \
  --ablate-field routing_hint \
  --agent-cmd "codex exec --model gpt-5.4 --sandbox workspace-write -c approval_policy=\"never\" --skip-git-repo-check"
```

The batch summary also includes `index_depth`, which records how many
`index.md` files were read, the deepest index depth reached, and whether the
agent read each ancestor index before moving on to concept files.

To summarize YAML fields read from non-index concept Markdown files, set
`--frontmatter-scope concept`. For a combined index/concept report, set
`--frontmatter-scope all`. Ablations default to index frontmatter for backward
compatibility; use `--ablate-scope concept` or `--ablate-scope all` to remove
fields from actual concept Markdown files.

```bash
python3 batch_runner.py \
  --task tasks/concept-frontmatter-canary.json \
  --variants concept-frontmatter-canary concept-frontmatter-sparse concept-frontmatter-expanded concept-frontmatter-quoted \
  --frontmatter-scope concept \
  --iterations 3 \
  --agent-cmd "codex exec --model gpt-5.4 --sandbox workspace-write -c approval_policy=\"never\" --skip-git-repo-check"
```

For the clean concept-file experiment, keep all `index.md` files body-routed
with no YAML and vary only the answer-bearing non-index concept files:

```bash
python3 scripts/build_concept_frontmatter_canary_bundle.py
python3 batch_runner.py \
  --task tasks/concept-frontmatter-canary.json \
  --variants concept-clean-body concept-clean-yaml-sparse concept-clean-yaml-okf \
  --frontmatter-scope concept \
  --iterations 30 \
  --jobs 3 \
  --shuffle-variants \
  --seed 1 \
  --agent-cmd "codex exec --model gpt-5.4 --sandbox workspace-write -c approval_policy=\"never\" --skip-git-repo-check"
```

For the applicable metadata-depth experiment, keep all `index.md` files
body-routed with no YAML, keep every non-index Markdown body identical across
variants, and vary only practical target concept YAML frontmatter. These
variants avoid task-specific hints and test how much normal metadata is needed:

```bash
python3 scripts/build_concept_frontmatter_canary_bundle.py
python3 batch_runner.py \
  --task tasks/concept-frontmatter-canary.public.json \
  --grade-task tasks/concept-frontmatter-canary.json \
  --variants concept-real-yaml-minimal concept-real-yaml-relational-lite concept-real-yaml-minimal-linked \
  --frontmatter-scope concept \
  --iterations 30 \
  --jobs 3 \
  --shuffle-variants \
  --seed 1 \
  --agent-cmd "codex exec --model gpt-5.4-mini --sandbox workspace-write -c approval_policy=\"never\" --skip-git-repo-check"
```

This matrix estimates the minimum useful concept-file frontmatter:
`concept-real-yaml-minimal` has identity plus required facts,
`concept-real-yaml-typed` adds classification metadata,
`concept-real-yaml-relational` adds related assets/signals/files, and
`concept-real-yaml-provenance` adds audit/provenance metadata. The follow-up
variants test whether frontloading decisive fields, trimming provenance to the
lowest useful set, or keeping only file-level relationships can beat the best
existing style without adding task-specific hints. The `minimal-linked`
follow-up isolates the strongest signal so far: minimal frontmatter plus
file-level relationships only.
The `.public.json` task is the agent-visible prompt; the private
`concept-frontmatter-canary.json` task keeps accepted answers and citation
expectations available only to the grader.

### Latest Batch (June 2026)

Current canary testing of metadata-depth variants (45 runs each, all successful):

| Variant | Accuracy | Duration (s) avg/med | Tokens avg/med | Citation Score | Trace Score | Files Read avg/med |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `concept-real-yaml-minimal` ⭐ | 1.0 | 42.6 / 41.0 | 14.5k / 11.5k | 1.0 | 1.0 | 4.2 / 4.0 |
| `concept-real-yaml-minimal-linked` | 1.0 | 43.0 / 41.9 | 14.7k / 12.1k | 1.0 | 1.0 | 4.4 / 4.0 |
| `concept-real-yaml-relational-lite` | 1.0 | 43.5 / 42.1 | 14.7k / 12.1k | 1.0 | 1.0 | 4.3 / 4.0 |

Key takeaways:

- All three leading variants achieved perfect accuracy, citation, and trace scores.
- `concept-real-yaml-minimal` is **the efficiency winner**: lowest average
  duration (~42.6s), lowest median tokens (~11.5k), fewest files read.
- File-relationship metadata (`minimal-linked`) adds ~30-50ms/run with no accuracy
  gain; relational metadata (`relational-lite`) costs 1-1.5s with no benefit.
- Identity + required facts only (no task hints, no relationships) is optimal for
  both performance and accuracy.

Run against a local llama.cpp server:

```bash
python3 batch_runner.py \
  --task tasks/enterprise-fnf-synthesis.json \
  --iterations 3 \
  --jobs 1 \
  --agent-cmd "python3 llama_cpp_agent.py --base-url http://127.0.0.1:8080/v1 --model local-model --mode instruct"
```

For this benchmark, prefer `--mode instruct`: the task is exact retrieval and
strict JSON output, not open-ended ideation. Use `thinking-coding` only if your
model needs more reasoning to navigate the corpus and still obeys the JSON
format.

For authoritative file-read traces, the runner exposes these environment
variables to the agent command:

- `OKF_TRACE_LOG`: path to a JSONL file where the command or wrapper can append
  runtime tool/file events.
- `OKF_BUNDLE_PATH`: absolute bundle path.
- `OKF_TASK_PATH`: absolute task path.
- `OKF_BUNDLE_VARIANT`: benchmark variant name.

Each `OKF_TRACE_LOG` line can be any of these shapes:

```json
{"type": "read_file", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"}
{"tool": "read_file", "arguments": {"path": "/commerce/metrics/net-margin.md"}}
{"action": "open", "file_path": "/platform/features/pricing-shadow-ledger.md"}
```

The runner also accepts stdout/stderr lines prefixed with `OKF_TRACE:` followed
by a JSON event. If runtime events are present, they replace the agent's
self-reported trace events before grading.

Run tests:

```bash
python3 -m pytest
```

## Agent Instructions

Give the agent one bundle path and the task in `tasks/synthesis.json`. The
agent should inspect `index.md` files first, follow links to relevant concepts,
and submit JSON using the schema below.

```json
{
  "task_id": "retail-margin-anomaly-v1",
  "bundle_variant": "strict",
  "answer": "Short synthesized answer.",
  "facts": {
    "root_cause": "...",
    "affected_metric": "...",
    "bad_join_key": "...",
    "rollout_id": "...",
    "remediation": "..."
  },
  "citations": [
    "/incidents/2026-06-margin-anomaly/root-cause.md",
    "/commerce/metrics/net-margin.md"
  ]
}
```

Optional trace schema:

```json
{
  "agent": "example-agent",
  "bundle_variant": "strict",
  "duration_ms": 42000,
  "events": [
    {"ts_ms": 0, "type": "read", "path": "/index.md"},
    {"ts_ms": 10200, "type": "read", "path": "/incidents/2026-06-margin-anomaly/root-cause.md"},
    {"ts_ms": 42000, "type": "answer"}
  ]
}
```

The grader treats `read`, `open`, `read_file`, `view`, and `inspect` events as
file reads. Trace scoring measures required files reached, unique files read,
duration, and whether distractor files were opened.

When using `agent_runner.py`, `duration_ms` is overwritten with runner-recorded
wall-clock time. File-read paths are authoritative when the external agent
command or wrapper emits runtime events through `OKF_TRACE_LOG` or `OKF_TRACE:`
lines; otherwise the runner falls back to the agent's self-reported trace.

## Testing Results

### Index File Metadata (June 2026)

Compared `index.md`-level frontmatter strategies:

| Variant | Accuracy | Duration (s) | Tokens | Trace Score |
| --- | --- | --- | --- | --- |
| `body-routed-indexes` | 1.0 | 42 | 17.5k | 0.96 |
| `sparse-index` | 1.0 | 48 | 16.0k | 0.97 |

**Finding:** Agents navigate equally well with minimal or no YAML on index files. Body-text routing cues (`## Key entries:` sections) are sufficient; dense index frontmatter adds no measurable benefit.

### Concept File Metadata (June 2026 — Current)

Tested concept-file frontmatter depth with body-routed indexes (no index YAML) and identical Markdown bodies:

| Variant | Accuracy | Duration (s, median) | Tokens (median) | Files Read |
| --- | --- | --- | --- | --- |
| `concept-real-yaml-minimal` | 1.0 | 41.0 | 11.5k | 4.0 |
| `concept-real-yaml-minimal-linked` | 1.0 | 41.9 | 12.1k | 4.0 |
| `concept-real-yaml-relational-lite` | 1.0 | 42.1 | 12.1k | 4.0 |
| `concept-frontmatter-expanded` | 0.98 | ~45 | ~16k | ~5.0 |
| `concept-clean-yaml-okf` | 1.0 | 34.6 | 12.2k | 8.0 |

**Finding:** Minimal frontmatter (identity + required facts only, no task hints) achieves perfect accuracy at lowest token cost. Added metadata (relationships, provenance) does not improve accuracy but costs extra tokens. Agents extract facts equally well from lean, focused YAML.

### Key Insight

Minimal, focused metadata outperforms both sparse and expanded variants. Agents effectively extract answers from lean frontmatter without needing:
- Task-specific hints in frontmatter
- Dense routing/inherited metadata
- Provenance or relationship fields

## What This Tests

- Parseability: markdown files with OKF-style YAML frontmatter can be parsed.
- Concept frontmatter: non-index Markdown files can carry decisive structured
  fields, not only directory `index.md` files.
- Progressive disclosure: broad `index.md` files point to deeper context.
- Accuracy: the final answer must use the deep, decisive concepts rather than
  plausible distractors.
- Citation discipline: the answer must cite the concepts that establish each
  required fact.
- Navigation speed and efficiency: optional traces show how quickly and cleanly
  the agent reached the decisive files.
- **Metadata minimalism:** what is the minimum necessary metadata density for
  reliable fact extraction?
