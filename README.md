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
- `bundles/frontloaded-yaml-retail-ops`: inverse extension. Directory `index.md`
  files start denser at the top and get lighter as you descend.
- `bundles/body-routed-indexes-retail-ops`: index files carry no YAML; routing
  cues live in the body with a `## Key entries:` section.
- `bundles/sparse-index-retail-ops`: index files keep only minimal frontmatter
  while concept files stay at uniform density.

The task is synthesis-oriented: the agent must combine facts from multiple
linked concepts to explain a fictional retail margin anomaly.

There are two task levels:

- `tasks/synthesis.json`: shallow baseline task over the original retail ops
  corpus.
- `tasks/deep-synthesis.json`: deeper navigation task over `deep-retail-ops`,
  requiring regional metric, experiment, identity-key, pipeline, incident, and
  remediation evidence.

## Run The Grader

Validate a bundle:

```bash
python3 grader.py --bundle bundles/strict-retail-ops --strict
python3 grader.py --bundle bundles/extended-retail-ops --extension
python3 grader.py --bundle bundles/uniform-yaml-retail-ops --extension
python3 grader.py --bundle bundles/frontloaded-yaml-retail-ops --extension
python3 grader.py --bundle bundles/body-routed-indexes-retail-ops --extension
python3 grader.py --bundle bundles/sparse-index-retail-ops --extension
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
- Progressive disclosure: broad `index.md` files point to deeper context.
- Accuracy: the final answer must use the deep, decisive concepts rather than
  plausible distractors.
- Citation discipline: the answer must cite the concepts that establish each
  required fact.
- Navigation speed and efficiency: optional traces show how quickly and cleanly
  the agent reached the decisive files.
