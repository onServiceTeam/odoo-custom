# 71 — Dispatch State Matrix

> Full transition table for `ons.dispatch`.

## Status definitions

| Code | Label | Terminal? | Description |
|------|-------|-----------|-------------|
| `draft` | Draft | No | Created but not submitted to marketplace |
| `pending_approval` | Pending Approval | No | Budget exceeds threshold; needs manager sign-off |
| `sent` | Sent | No | Posted to marketplace (WorkMarket) |
| `has_applicants` | Has Applicants | No | At least one pending applicant |
| `assigned` | Assigned | No | Worker accepted and assigned |
| `confirmed` | Confirmed | No | Customer or worker confirmed visit |
| `in_progress` | In Progress | No | Tech on-site or work underway |
| `completed` | Completed | Yes | Work finished |
| `cancelled` | Cancelled | Yes | Cancelled (worker may have been assigned) |
| `voided` | Voided | Yes | Voided before any worker assignment |

## Allowed transitions

| From | → Allowed Next Statuses |
|------|------------------------|
| `draft` | `pending_approval`, `sent`, `cancelled`, `voided` |
| `pending_approval` | `sent`, `cancelled`, `voided` |
| `sent` | `has_applicants`, `cancelled`, `voided` |
| `has_applicants` | `assigned`, `cancelled`, `voided` |
| `assigned` | `confirmed`, `cancelled`, `voided` |
| `confirmed` | `in_progress`, `cancelled`, `voided` |
| `in_progress` | `completed`, `cancelled` |
| `completed` | *(none — terminal)* |
| `cancelled` | *(none — terminal)* |
| `voided` | *(none — terminal)* |

## Timestamp side effects

| Transition Target | Timestamp Set |
|-------------------|---------------|
| `confirmed` | `confirmed_at` |
| `in_progress` | `started_at` |
| `completed` | `completed_at` |
| `cancelled` | `cancelled_at` |
| `voided` | `voided_at` |

## Business rules for specific transitions

| Transition | Rule |
|-----------|------|
| `draft → pending_approval` | Budget ≥ approval threshold |
| `draft → sent` | Budget < threshold OR already approved |
| `pending_approval → sent` | `approved_by` and `approved_at` must be set |
| `sent → has_applicants` | At least one `ons.dispatch.applicant` with status `pending` |
| `has_applicants → assigned` | Exactly one applicant `accepted` |
| Any → `cancelled` | `cancellation_reason` required |
| Any → `voided` | Only from pre-assignment statuses (draft/pending/sent/has_applicants) |

## "Needs Action" criteria

A dispatch needs action when:
- `dispatch_status = 'has_applicants'` (applicants waiting for review)
- `dispatch_status = 'sent'` AND has pending applicants
- Voice outcome = `reschedule_requested` (needs operator decision)
