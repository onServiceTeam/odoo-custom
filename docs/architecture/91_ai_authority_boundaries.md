# 91 — AI Authority Boundaries

## Core Principle

AI is **advisory** unless explicitly documented as **authoritative**.
Deterministic business logic (identity, billing, stage transitions, dispatch)
must never be silently overridden by AI output.

## Authority Matrix

| Domain | AI Role | Authority | Who Confirms |
|---|---|---|---|
| Intake classification | Suggest primary/secondary drivers | **Advisory** | Agent |
| Description polish | Suggest cleaned text | **Advisory** | Agent |
| Transcription | Store verbatim | **Authoritative** | None (raw capture) |
| Speaker diarization | Label agent/customer turns | **Advisory** | Heuristic fallback if AI fails |
| QA grading rubric | Deterministic v3 engine | **N/A** — not AI-driven | System |
| QA coaching feedback | Generate coaching notes | **Advisory** | Manager |
| Case summary | Generate summary | **Advisory** | Agent |
| Customer report | Generate customer-facing text | **Advisory + sanitized** | Agent before send |
| Copilot/architect chat | Answer questions | **Advisory** | Admin |
| Sentiment analysis | Compute score | **Advisory** — informational only | None |

## Protected Fields — AI Must Never Write Directly

These fields belong to deterministic business logic.
AI may **suggest** values that an action then validates, but never writes raw:

| Model | Protected Fields |
|---|---|
| `ons.interaction` | `state`, `partner_id` (identity resolution owns this) |
| `ons.case` | `stage_id`, `partner_id`, `assigned_tech_id`, all billing fields |
| `ons.dispatch` | `status`, `assigned_to_id`, `scheduled_date` |
| `crm.lead` | `stage_id`, `partner_id`, `probability` |
| `ons.customer.plan` | All fields (billing-authoritative) |
| `account.move` | All fields (accounting-authoritative) |

## Allowed AI Write Targets

| Model | AI-Writable Fields | Guard |
|---|---|---|
| `ons.interaction` | `primary_driver_id`, `secondary_driver_ids`, `ai_confidence`, `ai_classification_raw`, `issue_description` (polish) | Agent review + confidence threshold |
| `ons.case` | `summary` | Agent review |
| `ons.ai.run` | All fields | Audit log, always writable |

## Confidence Thresholds

From legacy code:

| Threshold | Meaning |
|---|---|
| ≥ 0.85 | High confidence — auto-populate driver, agent confirms |
| 0.70–0.84 | Medium — populate with visual warning |
| < 0.70 | Low — suggest but do not auto-fill; flag for manual classification |

## Failure Modes

| Failure | Behavior |
|---|---|
| API timeout | Log error in `ons.ai.run`, leave fields unchanged |
| Invalid driver codes | Silently drop to null (validated against DB) |
| Parse failure | Log raw response, leave fields unchanged |
| Budget exceeded | Block call, raise user warning |
| Task disabled | Raise user warning, no API call |
| Provider inactive | Raise user warning, no API call |

## Customer-Facing Output Rules

Customer reports and any customer-visible AI text must be:

1. Post-processed by `sanitize_for_customer()` logic
2. Free of: Discord refs, internal jargon, profanity, pricing patterns,
   AI-disclosure words ("AI", "Summary", "Automated", "Generated", "Bot")
3. Free of: "trust", "trusting", "trusted"
4. Plain text only — no markdown in customer output
5. 4-8 sentences maximum
6. Company name: "onService" (lowercase 'o')
