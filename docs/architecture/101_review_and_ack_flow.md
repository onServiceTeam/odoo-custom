# 101 — QA Review and Acknowledgement Flow

## State Machine

```
 draft ──→ graded ──→ in_review ──→ reviewed ──→ ack_pending ──→ acknowledged
                        ↑                                           │
                        └───────────── disputed ←───────────────────┘
```

### State definitions

| State | Meaning | Who acts |
|-------|---------|----------|
| `draft` | QA evaluation created, not yet scored | System / Manager |
| `graded` | Score calculated (auto or manual) | System |
| `in_review` | Flagged for manager review (auto-fail, low confidence, or dispute) | System |
| `reviewed` | Manager has reviewed and confirmed/overridden | Manager |
| `ack_pending` | Awaiting agent acknowledgement | System |
| `acknowledged` | Agent has signed off | Agent |
| `disputed` | Agent contests the evaluation → returns to in_review | Agent |

---

## Transitions

### 1. Create QA Evaluation → `draft`
- **Trigger:** Manager creates from call log, or auto-grading service creates
- **Required:** `call_log_id` with answered call & `agent_id`
- **Auto-compute:** `interaction_id`, `case_id` from call linkage

### 2. `draft` → `graded` (`action_grade`)
- **Trigger:** Score assigned (final_score set)
- **Side-effects:**
  - If `auto_fail = True` → set `needs_human_review = True`
  - If `needs_human_review` → next state is `in_review`
  - Otherwise → skip to `ack_pending`

### 3. `graded` → `in_review` (automatic if needs_human_review)
- **What happens:** Result appears in manager review queue

### 4. `graded` → `ack_pending` (automatic if no review needed)
- **What happens:** Result appears in agent's pending acknowledgements

### 5. `in_review` → `reviewed` (`action_review`)
- **Who:** Manager
- **Actions:**
  - Set `reviewed_by`, `reviewed_at`
  - Optionally set `override_score` (replaces final_score for aggregation)
  - Set `review_notes`
- **Next:** automatically → `ack_pending`

### 6. `reviewed` → `ack_pending` (automatic after review)
- **What happens:** Agent sees it in their pending queue

### 7. `ack_pending` → `acknowledged` (`action_acknowledge`)
- **Who:** Agent (self only — uid must match `agent_id`)
- **Actions:** Set `acknowledged_at = now()`
- **Terminal state** unless disputed later

### 8. `ack_pending` → `disputed` (`action_dispute`)
- **Who:** Agent
- **Required:** `dispute_reason` must be non-empty
- **Side-effects:** state reverts to `in_review` for manager re-evaluation

### 9. `disputed` → `in_review` (automatic)
- **What happens:** Result re-enters manager review queue with dispute context

---

## Coaching Flow

```
QA Result (graded) ──→ action_generate_coaching ──→ ons.qa.coaching (draft)
                                                        │
                                                        ↓
                                                   action_publish_coaching
                                                        │
                                                        ↓
                                                   coaching (published)
                                                        │
                                                        ↓
                                                   Agent sees coaching in UI
```

### Coaching states
| State | Meaning |
|-------|---------|
| `draft` | Created but not visible to agent |
| `published` | Manager approved, visible to agent |
| `acknowledged` | Agent has read it |

### Rules
- Coaching is always linked to exactly one `ons.qa.result`
- A result may have zero or one coaching artifact
- Coaching can be AI-generated (via ons.ai.run) or manually written
- Manager must publish before agent sees it
- Coaching is advisory — no domain write-backs

---

## Permission Matrix

| Action | Agent | Manager | Admin |
|--------|-------|---------|-------|
| View own results | ✅ | ✅ | ✅ |
| View all results | ❌ | ✅ | ✅ |
| Create result | ❌ | ✅ | ✅ |
| Grade result | ❌ | ✅ | ✅ |
| Review result | ❌ | ✅ | ✅ |
| Override score | ❌ | ✅ | ✅ |
| Acknowledge | ✅ (self) | ❌ | ❌ |
| Dispute | ✅ (self) | ❌ | ❌ |
| Create coaching | ❌ | ✅ | ✅ |
| Publish coaching | ❌ | ✅ | ✅ |
| View own coaching | ✅ | ✅ | ✅ |
| Manage rules | ❌ | ❌ | ✅ |
| Manage call types | ❌ | ❌ | ✅ |

---

## Aggregation Rules

- **Effective score** = `override_score` if set, else `final_score`
- **Agent averages** use effective score from acknowledged + reviewed results only
- **Pending count** = results where `state = 'ack_pending'` for the agent
- **Review queue** = results where `state = 'in_review'`
