# 72 — Dispatch ↔ Case Link Rules

> Governs when and how an `ons.case` produces an `ons.dispatch`.

---

## 1. Primary path: case → dispatch

| Step | Action |
|------|--------|
| 1 | Agent moves case to `onsite_dispatched` stage |
| 2 | Case appears in dispatch pending queue |
| 3 | Dispatcher creates `ons.dispatch` linked to case |
| 4 | Case `dispatch_id` populated, case stage already `onsite_dispatched` |

### Eligibility rules for case → dispatch

| Rule | Enforcement |
|------|-------------|
| Case stage = `onsite_dispatched` | Query filter on pending queue |
| No existing active dispatch | `dispatch_id = False` or linked dispatch is terminal |
| Case has `partner_id` | Required for customer details |
| Partner has address fields | Needed for location (can be entered during dispatch creation) |

---

## 2. Secondary path: standalone dispatch

A dispatch can be created without a case:
- From customer search (links to `partner_id` only)
- From manual entry (no case, no partner initially)

This covers ad-hoc field service requests that bypass the full
intake pipeline.

---

## 3. What the dispatch inherits from the case

| Dispatch Field | Source |
|---------------|--------|
| `partner_id` | `case.partner_id` |
| `title` | Generated: "On-Site Computer Repair — {city}" |
| `description` | `case.issue_description` |
| `contact_first_name` | `partner.name` (first word) |
| `contact_phone` | `partner.phone` |

Address fields are entered/confirmed during dispatch creation
(Google Places validation in future).

---

## 4. Backlinks from dispatch to case

| Field | Direction | Purpose |
|-------|-----------|---------|
| `ons.dispatch.case_id` | Dispatch → Case | Which case spawned this |
| `ons.case.dispatch_id` (computed) | Case → Dispatch | Active dispatch for this case |

---

## 5. One case, one active dispatch

A case may have at most ONE non-terminal dispatch at a time.
If a dispatch is cancelled/voided, a new one can be created.
Completed dispatches remain linked for history.

---

## 6. Status echo rules

| Dispatch Event | Effect on Case |
|----------------|---------------|
| Dispatch completed | No automatic case stage change — billing may follow |
| Dispatch cancelled | Case returns to `triage_in_progress` if not already further |
| Dispatch voided | Same as cancelled |

The case pipeline is NOT automatically driven by dispatch lifecycle.
The two lifecycles are linked but independent.
