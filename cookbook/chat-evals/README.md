# Collate AI Chat evals

Keep customer questions and expert expectations in CSV or JSON, run them through the same planner used by Collate AI Chat, and retain a JSON report for each run. `ai-sdk evals` supports validation, deterministic checks, optional semantic judging, external answers, and regression comparisons. Definitions and reports stay in files; there is no eval entity or server deployment to manage.

This follows the question → expert reference → agent response → verdict workflow described by [DataHub Context Evals](https://docs.datahub.com/docs/features/feature-guides/context/context-evals) and its [CLI](https://docs.datahub.com/docs/cli-commands/evals). This first version provides a file-based workflow; it does not add a validation UI, server-side schedules, automatic case generation, or unpublished-context previews.

## Build and try it offline

Build this checkout; previously released binaries do not contain these commands:

```bash
cd cli
cargo build --release
cd ..
export PATH="$PWD/cli/target/release:$PATH"

ai-sdk evals validate -f cookbook/chat-evals/smoke.csv
ai-sdk evals report -f cookbook/chat-evals/smoke.csv \
  --answers cookbook/chat-evals/sample-answers.json \
  -o /tmp/collate-evals-offline.json
```

The cases in `smoke.csv` and `cases.json`, and the answers in `sample-answers.json`, are **fictional examples**. Replace their FQNs, owners, schema, business definitions, and dates before running against a customer. The smoke suite tests configured assertions only; passing it does not establish SQL or business correctness. Use expert references and semantic judging for that.

## Run against Collate AI Chat

Existing `ai-sdk configure` profiles work, or set:

```bash
export AI_SDK_HOST="https://your-instance.getcollate.io"
export AI_SDK_TOKEN="your-user-or-bot-jwt"

ai-sdk evals run -f cookbook/chat-evals/smoke.csv \
  --label before-context-update -o before.json
```

By default each case creates a new chat conversation and invokes `PLANNER` / `CHAT_MODE` at `/api/v1/agents/invoke`. The agent receives **only the question**. Expert answers, SQL, assertions, and rubrics go to the grader. Fresh conversations avoid contamination from previous answers; requests disable response caching. The existing user's persona, preferences, memories, permissions, and Query Runner credential resolution still apply. Run before/after comparisons under the same identity and use fixed date windows.

`run` executes real chat behavior: it persists conversations and can execute warehouse SELECTs and save reusable queries. Repeated runs can therefore change the saved-query context available to later runs. Freeze or account for those changes when benchmarking context edits. The CLI does not publish or edit context itself.

An API-enabled AI Studio agent can be evaluated with `--agent NAME`. The internal `WorkerAnalyticsAgent` seed is a planner worker, not an external API-enabled agent; the default target is the customer-facing path to evaluate it in context.

## Semantic answer and SQL judging

```bash
export EVAL_JUDGE_TOKEN="your-judge-api-key"
export EVAL_JUDGE_MODEL="your-structured-output-capable-model"

ai-sdk evals run -f cookbook/chat-evals/cases.json \
  --judge llm --judge-model "$EVAL_JUDGE_MODEL" \
  --label before-context-update -o before.json

# After updating the relevant glossary definitions, metrics, or shared memories:
ai-sdk evals run -f cookbook/chat-evals/cases.json \
  --judge llm --judge-model "$EVAL_JUDGE_MODEL" \
  --label after-context-update -o after.json

ai-sdk evals compare before.json after.json
```

The judge defaults to OpenAI's Chat Completions URL. `--judge-url FULL_URL` supports another endpoint implementing the same request and response format, including strict `json_schema` output. The implementation follows the official [Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) and [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat) contracts. The judge receives the question, expert reference, rubric, answer, and answer components, including returned rows; configure an appropriate endpoint for the customer's data. The Collate JWT is not sent to the judge.

SQL judging compares intent, source tables, joins, filters, grain, aggregation, null handling, and date boundaries. SQL comes from structured table/chart query configuration or SQL code components, because the final prose often omits it. Components explicitly marked `isAnswer: false` and running SQL are excluded from grading. A configured SQL reference without structured SQL evidence fails, including on older server versions that omit components. A failed answering SQL component also fails.

This is an LLM assessment of equivalence, not a formal SQL proof or a comparison of separately executed reference results. The harness never executes the expert SQL. For numeric correctness, include a known expected answer against a stable dataset as well. Keep human-reviewed gold cases to calibrate the judge. Cases with a rubric require `--judge llm`; missing configuration and malformed/refused/truncated judge responses produce errors rather than passing.

## Case format

### Banking example tested on devrel

[banking-devrel.csv](banking-devrel.csv) contains three standalone questions derived from [this banking conversation](https://devrel.getcollate.io/conversations/88650faa-3670-4457-9af0-c82d906151df). The reference values were checked by re-executing its reporting SQL against `banking-redshift` on October 28, 2026. The fixture requires structured answer SQL as well as its configured text/reference checks.

The reference definition uses `fct_trades.total_commission`, whose total is 299,377, and fee mart totals of 22,422 (ATM), 169,840 (wire), and 241,195 (account), giving 732,834. Raw trades produced a different commission total during the live test. The broad questions intentionally leave discovery open, so differences can reveal a source-definition mismatch rather than an arithmetic bug. A number merely mentioned as an alternative can satisfy a substring check; use a semantic rubric when the primary conclusion matters.

[banking-devrel-marts.csv](banking-devrel-marts.csv) and its equivalent [JSON definition](banking-devrel-marts.json) make the reporting sources explicit. This case passed the live run with the expected 732,834 total and a structured SQL result. These are dated dataset snapshots; recheck the reference values when the demo data changes.

```bash
ai-sdk evals run -f cookbook/chat-evals/banking-devrel-marts.csv -o banking-run.json
```

### Fields

JSON is an array of case objects. CSV uses the same field names as column headers, with `|` separating values in array fields. Use standard CSV quoting for commas, quotes, and multiline questions or SQL. Use JSON if an array value itself contains `|`.

| Field | Meaning |
| --- | --- |
| `id` | Required unique, stable case identifier. |
| `question` | Required exact customer question. |
| `expected_answer` | Expert reference answer. Exact mode compares text with normalized whitespace; LLM mode judges meaning. |
| `expected_sql` | Expert SQL. Exact mode requires an identical structured statement except outer whitespace; LLM mode assesses equivalence. |
| `guidelines` | Additional semantic pass criteria; requires LLM mode. |
| `contains`, `not_contains` | Case-insensitive substring checks against answer prose. |
| `must_reference`, `must_not_reference` | Exact catalog FQNs in final-answer catalog links, component entity references, asset components such as lineage/profile, or SQL code provenance. These check references, not parsed SQL table usage; express SQL source constraints in the rubric. |
| `required_tools` | Exact names in `toolsUsed`. Missing tool trace fails the check. Avoid this unless a tool path itself is the behavior being tested. |
| `require_sql` | Boolean, default `false`. Require structured answer SQL without requiring an exact statement or an LLM judge. CSV accepts `true`, `false`, or an empty cell. |

At least one reference, rubric, or assertion is required. All configured checks must pass. Empty suites, duplicate IDs, unknown fields, and blank assertion values are rejected. Optional reference fields may be omitted or null; empty CSV cells become null. JSON arrays default to empty.

`validate` checks the file without credentials or API calls. It accepts rubric cases regardless of eventual judge choice; execution checks that the selected judge can grade them. Add/edit/delete cases in the file and keep it in version control. `--id revenue-owner,completed-revenue` selects a subset; unknown IDs are errors. `--timeout 900` bounds each complete case, including grading. A timed-out server request may continue remotely; this CLI does not cancel it or automatically retry invocations.

## Reports, comparisons, and CI

Every report records the run ID, timestamp, label, target, judge configuration, full case definitions, conversation IDs, answer components, available usage, per-check reasoning, duration, and `PASS` / `FAIL` / `ERROR`. Credentials and intermediate thinking are not written. Reports are flushed after each case, created with owner-only permissions on Unix, and never overwrite an existing path. An interrupted run is marked incomplete when its last report snapshot is intact; comparisons reject incomplete files. Use a new output filename per run.

```bash
jq '.results[] | {id: .case.id, status, checks, error}' after.json
jq '[.results[] | select(.status == "PASS")] | length' after.json
```

`run` and `report` exit `0` only when every selected case passes, and `1` on any failure or error. Case errors are recorded and execution continues with the remaining cases. The terminal prints the pass rate, including errors in the denominator.

`compare` emits JSON listing regressions, improvements, changed definitions, removed cases, and additions. It exits `1` for a previous PASS becoming FAIL/ERROR, changed case definitions, or removed cases. It rejects mismatched judge settings. It can compare different targets intentionally, but use the same identity and target for context-only experiments. It is a regression gate, so a case failing in both runs is not a new regression; use `run` to enforce all-pass acceptance. Reports in a versioned artifact directory provide run history.

For CI, build the CLI, export the credentials as secrets, run the suite, and upload the output JSON even if the command exits `1`. A scheduler or cron can invoke the same command with a unique output path for periodic checks. Neither scheduling nor artifact hosting is built into this CLI.

## Grade answers from another harness

The input is a JSON object keyed by stable case ID. Each value needs `response`; `components`, `toolsUsed`, `usage`, and `conversationId` are optional. See [sample-answers.json](sample-answers.json). Missing selected answers become ERROR; unknown IDs are rejected.

```bash
ai-sdk evals report -f cookbook/chat-evals/cases.json \
  --answers my-agent-answers.json \
  --judge llm --judge-model "$EVAL_JUDGE_MODEL" -o external-run.json
```

`report` does not call Collate. Exact-mode reporting needs no network or credentials; LLM reporting calls only the configured judge.

## Why evaluate the planner path?

The implementation was traced in local Collate checkout `43446edf49` and AI Platform checkout `627149644`:

1. Collate's [`AgentResource`](https://github.com/open-metadata/openmetadata-collate/blob/43446edf49/collate-service/src/main/java/io/collate/resources/agents/AgentResource.java) routes synchronous invocation through [`AgentExecutionService`](https://github.com/open-metadata/openmetadata-collate/blob/43446edf49/collate-service/src/main/java/io/collate/service/agents/AgentExecutionService.java), which collects answer text, tools, thinking, and typed components from the same runtime used by streaming chat.
2. AI Platform's [`PlannerAgentBuilder`](https://github.com/open-metadata/ai-platform/blob/627149644/agent/src/main/kotlin/io/getcollate/ai/agent/builder/PlannerAgentBuilder.kt) discovers workers, plans and dispatches dependent steps, checks progress, and synthesizes one response. [`PlannerAgentPrompts`](https://github.com/open-metadata/ai-platform/blob/627149644/agent/src/main/kotlin/io/getcollate/ai/agent/prompt/PlannerAgentPrompts.kt) routes discovery and definition lookup to search and data questions to analytics. Thus a wrong answer can originate before the analytics worker runs.
3. Collate's [`WorkerAnalyticsAgent` seed](https://github.com/open-metadata/openmetadata-collate/blob/43446edf49/collate-service/src/main/resources/json/data/ai/dynamicAgent/workerAnalyticsAgent.json) defines SQL and visualization behavior. AI Platform's [`GenerateSqlTool`](https://github.com/open-metadata/ai-platform/blob/627149644/agent/src/main/kotlin/io/getcollate/ai/agent/tool/analysis/GenerateSqlTool.kt) implements generation/execution, with reusable-query and saved-metric paths. The [analytics grounding guide](https://github.com/open-metadata/ai-platform/blob/627149644/docs/analytics-context-and-grounding.md) describes entity context, profiles, schema/constraints, and shared memories as query-time inputs.
4. [`ComponentBuilder`](https://github.com/open-metadata/ai-platform/blob/627149644/agent/src/main/kotlin/io/getcollate/ai/agent/component/ComponentBuilder.kt) attaches SQL provenance to tables and charts; failed or empty results can arrive as code components. The planner preserves those components for the user. Grading the final prose alone would miss this evidence.

Start a customer suite with canonical-asset discovery, metric definitions, governed-metric reuse, date/filter correctness, join grain, shared-memory caveats, and ambiguity handling. Run the same suite before and after a context change, inspect each failing case's evidence and reasoning, and correct the source context or an overly strict test as appropriate. The verdict alone does not establish the root cause.
