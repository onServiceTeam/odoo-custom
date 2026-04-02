# 90 — AI Services Contract

## Scope

`ons_ops_ai` owns the **AI service abstraction layer** inside Odoo.
It does **not** call external AI APIs directly — actual inference runs
in the Node.js sidecar just as it does today.  Odoo owns:

| Responsibility | Owner |
|---|---|
| Provider/model configuration | `ons_ops_ai` (Odoo) |
| Task → model routing table | `ons_ops_ai` (Odoo) |
| Prompt contract / template storage | `ons_ops_ai` (Odoo) |
| Run log & cost tracking | `ons_ops_ai` (Odoo) |
| Actual OpenAI/Anthropic HTTP calls | Node.js sidecar (unchanged) |
| Transcription scheduling & retry | Node.js sidecar (unchanged) |
| TTS / voice synthesis | Node.js sidecar (unchanged) |

## AI Use Cases Modeled

These are the use cases proven from legacy code that get Odoo-side models:

| # | Use Case | Task Type | Advisory vs Authoritative | Sidecar Calls API? |
|---|---|---|---|---|
| 1 | Intake classification | `intake_classification` | Advisory — agent confirms | Yes |
| 2 | Description polish | `description_polish` | Advisory — agent reviews | Yes |
| 3 | Combined polish + classify | `polish_and_classify` | Advisory | Yes |
| 4 | Audio transcription | `transcription` | Authoritative (stored verbatim) | Yes |
| 5 | Speaker diarization | `diarization` | Advisory (heuristic fallback) | Yes |
| 6 | QA grading | `call_grading` | Deterministic engine (v3), AI only for diarization | Yes (diarization only) |
| 7 | Coaching insights | `coaching_insights` | Advisory — manager reviews | Yes |
| 8 | Case/ticket summary | `ticket_summary` | Advisory — agent reviews | Yes |
| 9 | Customer report | `customer_report` | Advisory then sanitized | Yes |
| 10 | QA architect copilot | `copilot_reasoning` | Advisory — admin only | Yes |

## Models

### `ons.ai.provider`
Central provider registry.  Maps to legacy `ai_provider_config`.

- `name` — unique machine key (`openai`, `anthropic`)
- `display_name`
- `provider_type` — `chat` | `transcription` | `embedding` | `tts`
- `api_endpoint` — base URL
- `is_active` — only one active per type
- `config_json` — encrypted JSON blob (API key, org, etc.)
- `last_health_check` / `health_status`

### `ons.ai.model`
Model catalog.  Maps to legacy `ai_models`.

- `model_id` — unique (`gpt-4o`, `gpt-4o-mini`, `whisper-1`, `o1`)
- `provider_id` → ons.ai.provider
- `category` — `chat` | `reasoning` | `transcription` | `embedding` | `tts`
- `capabilities` — Text (one per line: reasoning, fast, cheap, vision)
- `pricing_tier` — budget | standard | premium
- `input_cost_per_1k` / `output_cost_per_1k`
- `max_tokens` / `context_window`
- `is_available`

### `ons.ai.task`
Task → model routing.  Maps to legacy `ai_task_models`.

- `task_type` — unique code
- `display_name` / `description`
- `model_id` → ons.ai.model
- `fallback_model_id` → ons.ai.model
- `temperature` (0.0–2.0)
- `max_tokens`
- `is_enabled`
- `prompt_template_id` → ons.ai.prompt.template (optional)

### `ons.ai.prompt.template`
Stored prompt contracts.  New — legacy has inline prompts only.

- `code` — unique machine key
- `name`
- `task_type` — links to the task it serves
- `system_prompt` — the system message (supports `{{variable}}`)
- `user_prompt_template` — user message template (supports `{{variable}}`)
- `available_variables` — docs field
- `version` — integer, incremented on change
- `is_active`

### `ons.ai.run`
Audit log of every AI invocation.  Maps to legacy `ai_usage_log`.

- `task_type`
- `model_id` → ons.ai.model
- `requested_model` / `actual_model` — Char (detect drift)
- `input_tokens` / `output_tokens`
- `total_cost`
- `duration_ms`
- `success` — Boolean
- `error_message`
- `res_model` / `res_id` — polymorphic link to source record
- `user_id`
- `request_summary` — truncated input (first 500 chars)
- `response_summary` — truncated output (first 500 chars)

### `ons.ai.budget`
Budget enforcement config.  Maps to legacy `integration_settings.ai_budget`.

- `daily_limit` — Monetary
- `monthly_limit` — Monetary
- `alert_threshold_pct` — Integer (default 80)
- `daily_spent` / `monthly_spent` — computed from run log
- `is_over_budget` — computed Boolean

### Inherited models
- `ons.interaction` — add `ai_run_ids` (O2M to ons.ai.run via res_model/res_id)
  and action buttons for manual AI re-run
- `ons.case` — add `ai_run_ids` and summary generation action

## What This Prompt Does NOT Build

- No direct HTTP calls to OpenAI/Anthropic from Odoo
- No transcription scheduler (stays in sidecar)
- No TTS synthesis (stays in sidecar)
- No QA engine rewrite (Prompt 11)
- No Discord bot AI features (stays in sidecar)
- No real API key management UI (keys live in sidecar env/config)

## Data Flow

```
Sidecar                          Odoo
───────                          ────
1. Sidecar calls OpenAI     →   (nothing)
2. Sidecar gets result       →   POST /api/ai/log_run  →  creates ons.ai.run
3. Sidecar writes result     →   PATCH interaction fields (driver, confidence, etc.)
4. Agent clicks "Classify"   →   Odoo calls sidecar endpoint
                             ←   Sidecar returns result
                             →   Odoo creates ons.ai.run + updates interaction
5. Agent clicks "Summarize"  →   Same pattern
```

The sidecar remains the only process with API keys.
Odoo stores the config/routing/audit layer.

## Safety Invariants

1. AI never silently overwrites deterministic fields (stage, billing, identity)
2. Classification is always advisory — `ai_confidence` < 1.0 means "suggested"
3. Polish preserves all original facts, names, phone numbers verbatim
4. Customer reports are post-sanitized (no internal jargon, no AI disclosure)
5. Budget enforcement blocks calls when over-limit
6. Every AI call creates an `ons.ai.run` record — no silent invocations
7. Prompt templates are versioned — changes create new version, old is deactivated
8. Task types can be individually disabled without code changes
