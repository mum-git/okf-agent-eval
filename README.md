# OKF Agent Evaluation

This is a standalone benchmark for testing whether an agent can navigate and
use an OKF-style knowledge bundle without losing parseability or accuracy.

It includes three equivalent knowledge bundles:

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
- `bundles/body-routed-indexes-retail-ops`: index files carry no YAML; routing
  cues live in the body with a `## Key entries:` section.
- `bundles/sparse-index-retail-ops`: index files keep only minimal frontmatter
  while concept files stay at uniform density.
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
- `bundles/concept-real-yaml-minimal-retail-ops`: applicable sparse baseline;
  identity fields plus required domain facts, with no task-specific hints.
- `bundles/concept-real-yaml-typed-retail-ops`: same real bundle, with normal
  classification metadata such as domain, system, status, and owner.
- `bundles/concept-real-yaml-relational-retail-ops`: same real bundle, with
  relationship metadata for related assets, signals, and files.
- `bundles/concept-real-yaml-provenance-retail-ops`: same real bundle, with
  provenance and verification metadata.
- `bundles/concept-real-yaml-frontloaded-retail-ops`: same real bundle, with
  decisive operational fields placed first in each target concept frontmatter.
- `bundles/concept-real-yaml-provenance-lite-retail-ops`: same real bundle,
  with lean provenance metadata and duplicated provenance noise removed.
- `bundles/concept-real-yaml-relational-lite-retail-ops`: same real bundle,
  with only practical file relationship metadata, not repeated asset/signal
  relationship fields.
- `bundles/concept-real-yaml-minimal-linked-retail-ops`: same real bundle,
  with minimal answer-bearing metadata plus only practical file relationship
  metadata.
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

### Latest Batch

The most recent completed batch before billing exhaustion was the older
control-vs-YAML comparison. The averages and medians below are computed over
successful runs only.

| Variant | Pass/Fail | Accuracy avg/med | Total avg/med | Duration avg/med (s) | Tokens avg/med | Speed avg/med | Files avg/med |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `concept-real-control` | 9/21 | 0.0000 / 0.0000 | 0.4655 / 0.5000 | 168.3 / 155.4 | 76,715 / 60,115 | 0.1888 / 0.1931 | 9.22 / 9.00 |
| `concept-real-yaml-sparse` | 8/22 | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 37.0 / 38.2 | 16,287 / 9,754 | 0.8053 / 0.7850 | 6.13 / 6.50 |
| `concept-real-yaml-okf` | 8/22 | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 35.3 / 34.0 | 20,838 / 22,240 | 0.8702 / 0.8832 | 6.25 / 6.50 |

Key takeaways:

- `concept-real-control` is not a useful repeated-test candidate: it had `0.0`
  factual accuracy and materially worse runtime/token behavior.
- `concept-real-yaml-sparse` and `concept-real-yaml-okf` both reached perfect
  factual accuracy, citation score, and trace score on all successful runs.
- `concept-real-yaml-okf` was slightly faster on average/median duration, while
  `concept-real-yaml-sparse` used fewer median tokens. That difference is
  directional, not conclusive, because the batch was cut short by billing.

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
