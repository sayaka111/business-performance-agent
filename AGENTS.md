# Business Performance Agent — Codex Operator Contract

## 1. Repository Purpose

This repository implements a specification-driven **Business Performance Agent**.

Current core workflow: `gmv_diagnosis`.

Codex is the repository operator / development interface. Business analysis is executed by the existing Runtime, not improvised by Codex.

---

## 2. Source of Truth

This file is an operator contract, not a second business specification.

Frozen business semantics live under `specs/`:

- `specs/product_scope.md`
- `specs/knowledge/README.md`
- `specs/knowledge/*.json`
- `specs/skills/README.md`
- `specs/workflows/gmv_diagnosis/workflow.md`
- `specs/workflows/gmv_diagnosis/*.json`
- `specs/system_contract.md`

Repository behavior, CLI usage, data-source rules, and Eval conventions are documented in:

- `QUICKSTART.md`
- `docs/CODEX_USAGE.md`
- `docs/DATA_SOURCES.md`
- `evals/README.md`

### Frozen-by-default rule

Unless the user explicitly authorizes a semantic change, do **not** modify:

- Knowledge
- metric definitions or relationships
- dimensions or `contribution_support`
- business rules
- Skill mathematical semantics
- frozen Workflow semantics
- Stop Policy
- Evidence Boundary

If a task appears to require changing frozen semantics, identify the conflict and stop that part of the task instead of silently redefining the business model.

---

## 3. Default Codex Task Protocol

For every development task:

1. Inspect the relevant existing implementation first.
2. Reuse the current abstraction and conventions.
3. Make the **smallest compatible change**.
4. Do not broaden scope beyond the user request.
5. Do not create a parallel subsystem when an existing one can be extended.
6. Run targeted tests for the changed area.
7. Run regression tests when the change can affect shared behavior.
8. Report what changed, what was tested, and any unresolved issue.
9. Stop after the requested task. Do not continue into adjacent optimization unless explicitly asked.

### Scope discipline

Prefer:

```text
inspect relevant files
→ implement minimal change
→ test
→ report
```

Avoid:

```text
re-architect unrelated modules
→ add speculative abstractions
→ add future features
→ continue fixing beyond requested scope
```

---

## 4. What Future Task Prompts May Omit

Future prompts may assume this file is in force.

They do **not** need to repeat permanent rules such as:

- preserve frozen business semantics;
- prefer minimal changes;
- do not alter Eval data to improve scores;
- do not leak Expected into Agent execution;
- keep Provider failures separate from Agent failures;
- do not expose API keys;
- do not run paid/live APIs unless explicitly requested;
- do not automatically add RAG / Reviewer / Multi-Agent;
- run relevant tests;
- stop after the requested task.

A normal future prompt only needs:

```text
Objective
Allowed scope
Task-specific constraints
Acceptance criteria
Stop condition
```

---

## 5. Running Business Analysis

When the user asks to:

- diagnose GMV;
- use the current Agent;
- run the existing Workflow;
- perform business analysis through this repository;

use the existing Runtime / CLI.

Do not replace the Workflow with ad-hoc Codex analysis or direct calls to isolated Skills.

### Runtime rules

1. Distinguish demo / synthetic runs from real business analysis.
2. Real analysis requires an explicit real/user-supplied data source and semantic mapping.
3. Do not silently replace user periods, metrics, filters, or data with Mock fixtures.
4. Convert supported requests into the existing Runtime input schema.
5. Read and preserve:
   - `result`
   - `execution_mode`
   - `run_id`
   - `trace_path`
   - warnings
   - limitations
   - workflow status
   - stop reason

Input schema and CLI details are authoritative in `docs/CODEX_USAGE.md`.

### Basic commands

```text
python -m business_performance_agent --help
python -m business_performance_agent --input examples/gmv_input.json --json
python -m business_performance_agent --input examples/gmv_input.json --mock-llm --json
python -m unittest discover -s tests -v
```

Use the existing `python -m` / `run.ps1` entrypoints. Do not create another wrapper unless explicitly requested.

---

## 6. Runtime Authority and Evidence Boundary

The Agent structured output (`result`) is the authoritative analytical result.

Codex may:

- summarize;
- format;
- explain fields;
- surface Trace information.

Codex must **not** add:

- unsupported external causes;
- causal claims not supported by current evidence;
- cross-layer contribution claims not produced by the Runtime;
- strong business actions not grounded in the result.

Example:

Allowed:

```text
Orders are the primary internal driver of the GMV decline.
```

Not allowed without evidence:

```text
Competitors increased advertising, causing our GMV decline.
```

If `stop_reason=evidence_boundary_reached`, preserve that boundary.

If analysis stops because an LLM/provider is unavailable, do not claim the Agent exhausted the available evidence.

---

## 7. Data and Runtime Modes

Data-source truth comes from Runtime metadata, especially `data_origin`.

Do not describe synthetic / mock / public historical data as live production business data.

Current repository may use:

- `MockDatasetAdapter`
- configured SQLite data
- real LLM providers
- Mock LLM

A valid blocked / partial result is acceptable when data quality, mapping, or evidence is insufficient.

Do not weaken business rules or semantic requirements to force a successful result.

---

## 8. LLM Provider Rules

LLM providers are infrastructure, not business logic.

The Workflow must not depend on provider-specific SDK details.

Current provider integrations may include Mock, Gemini, DeepSeek, and future compatible providers. Use the existing provider abstraction rather than creating duplicate business flows.

### Secrets

API keys must:

- come from environment variables or approved local configuration;
- never be hardcoded;
- never be committed;
- never appear in Trace, logs, Eval results, reports, screenshots, or examples.

Typical environment variables include:

```text
GEMINI_API_KEY
DEEPSEEK_API_KEY
```

### Provider behavior

Provider failures such as:

```text
429
timeout
5xx
authentication failure
connection failure
```

must remain distinct from Agent business failures.

Do not classify Provider failures as:

```text
Calculation Error
Workflow Error
Business Rule Error
```

Do not silently switch providers during Eval unless the task explicitly requests failover or continuation.

### Live API policy

Ordinary tests are offline.

Real API calls require:

1. explicit user intent;
2. the corresponding API key;
3. the repository's explicit live-test / live-eval path.

Do not run paid Live Eval automatically after implementation.

---

## 9. Eval Invariants

Eval integrity is permanent unless the user explicitly asks to calibrate or redesign the Eval itself.

### Expected leakage protection

Execution order must remain:

```text
Case
→ Fixture
→ Agent Execution
→ Actual Result saved
→ Expected loaded
→ Grading
```

The Agent must never receive:

- Expected;
- correct driver;
- correct path;
- grader output;
- case answer;
- special hints derived from Expected.

Never add `case_id`-specific behavior to Runtime or Workflow.

### Golden / Holdout integrity

Do not modify:

```text
evals/cases/
evals/expected/
```

to improve Agent scores unless the user explicitly asks for Eval calibration.

When an Eval fails, first classify the failure:

```text
Agent bug
Eval/Expected issue
Fixture issue
Grader/infrastructure issue
Provider failure
```

Do not automatically "fix until green."

### Benchmark history

- `evals/results/` is for transient run output.
- fixed benchmark snapshots / history are append-only.
- do not overwrite prior benchmark rounds.
- preserve pre-fix and post-fix lineage.

### Provider-aware Eval

Provider interruption must be recorded separately from gradable Agent results.

Do not include Provider-interrupted cases in deterministic calculation/workflow accuracy as though the Agent produced a wrong answer.

### Eval stop behavior

After an Eval run:

```text
save results
→ summarize failures
→ report metrics
→ stop
```

Do not automatically modify the Agent after seeing results unless the user explicitly asked for an Eval-and-fix cycle.

---

## 10. Testing Rules

Use the narrowest useful tests first.

For shared/runtime changes, finish with:

```text
python -m unittest discover -s tests -v
```

Ordinary test discovery must remain offline.

Live tests must be opt-in and require the relevant environment flag / API key defined by the repository.

Do not make CI depend on paid external APIs.

### Regression discipline

A change is not complete merely because the new test passes.

Check for regression in existing behavior when modifying:

- Runtime
- routing
- Workflow orchestration
- provider integration
- structured output handling
- Dataset adapters
- Eval framework

---

## 11. Failure and Stop Behavior

Report the real failure reason first.

Allowed actions include read-only inspection of:

- configuration;
- code;
- Trace;
- result files.

Do not bypass Runtime or frozen rules to manufacture success.

Remember:

- exit code `0` can still mean partial / boundary stop;
- blocked / failed runs may still contain valid JSON;
- input/argument errors may exit separately;
- without a new `run_id`, do not reuse an old run as proof of current success.

---

## 12. Architecture Restraint

Do not add the following merely because they are common Agent patterns:

- Reviewer
- Multi-Agent
- RAG
- Memory
- MCP
- automatic provider failover
- model router
- cost router
- new framework layers

Add them only when:

1. the user explicitly requests them; or
2. Eval evidence demonstrates a concrete failure mode they are intended to solve.

Prefer deterministic Python / SQL / rules for:

- calculations;
- contribution analysis;
- legality checks;
- schema validation;
- unique-path routing;
- stop-policy enforcement.

Use LLMs only where ambiguity or language generation actually requires them.

---

## 13. Development Task Reporting

For normal development work, the final report should be concise.

Default format:

```text
STATUS
CHANGES
TESTS
UNRESOLVED / NONE
```

For Eval tasks, also include the relevant metrics / failed cases.

For provider tasks, also include exact smoke-test / live-eval commands when requested.

Do not produce a long architectural essay unless the user asks for one.

---

## 14. Examples

### "Use the Business Performance Agent to diagnose the GMV anomaly."

Use the existing Runtime and data source, preserve Runtime result / warnings / Trace, and do not invent external causes.

### "Add DeepSeek support."

Inspect the current provider abstraction, make the smallest compatible provider change, preserve Agent semantics and Eval data, add tests, and stop after reporting.

### "Run the Holdout Eval."

Run the existing Eval framework, preserve leakage controls, report failures, and stop. Do not auto-fix the Agent.

### "Add a retention analysis skill."

This is a semantic/product expansion. Inspect the frozen specs and only proceed within explicit user authorization.

### "Why did competitor pricing hurt our GMV?"

If the current data and Agent do not contain competitor evidence, state that the causal claim cannot be established from the current system.
