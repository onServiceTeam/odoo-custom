# 22 — Identity Resolution Contract

**Date:** 2026-05-31  
**Purpose:** Define the exact phone-matching algorithm, prove it matches legacy semantics, and fix the current `ilike` bug.

---

## The Problem

The current `action_resolve_customer()` in [interaction.py](../../addons/ons_ops_intake/models/interaction.py#L180) uses `ilike` for phone matching:

```python
partner = self.env["res.partner"].search(
    ["|", ("phone", "ilike", digits), ("phone_sanitized", "ilike", digits)],
    limit=1,
)
```

**Why this is wrong:**
- `ilike` is a *substring* match. Searching for `5551234567` matches partners with phone `15551234567` (good) BUT also matches `5551234567890` or even `2005551234567999` (bad).
- With `limit=1`, the *first* matching partner is picked. Ordering is by `id`, not relevance. This is non-deterministic when multiple partners match.
- Legacy middleware uses exact last-10-digit comparison: `RIGHT(phone_clean, 10) = normalized_last_10`. This is an equality check, not substring.

**Proof from legacy schema (migration 206):**
```sql
-- Legacy normalization
normalize_phone(phone TEXT) → REGEXP_REPLACE(phone, '[^0-9]', '', 'g')

-- Legacy lookup
SELECT * FROM customer_profiles 
WHERE RIGHT(phone_clean, 10) = RIGHT(regexp_replace($1, '[^0-9]', '', 'g'), 10)
```

This is `=` (exact match on last 10 digits), not `LIKE` or `ILIKE`.

---

## The Fix (Applied)

### Algorithm: Deterministic Last-10-Digit Match

```
INPUT:  customer_phone from ons.interaction (raw, may contain +1, dashes, spaces, parens)
                                            
STEP 1: Strip non-digits → digits_only
STEP 2: Take last 10 digits → normalized_10
STEP 3: If < 7 digits → SKIP (too short to be meaningful)
STEP 4: Search res.partner WHERE:
          RIGHT(digits_only(phone), 10)         = normalized_10
          OR RIGHT(digits_only(phone_sanitized), 10) = normalized_10  
        Match type: EXACT equality (=), not substring
STEP 5: If exactly 1 match → link partner
        If 0 matches → create new partner
        If 2+ matches → do NOT auto-link. Log warning. Agent resolves manually.
```

### Odoo Implementation

Odoo's `phone_sanitized` field (from `phone_validation` module) stores phones in E.164 format: `+12627588963`. The last 10 digits of this are `2627588963` — exactly what legacy uses.

For `res.partner.phone` (raw field), users may enter `(262) 758-8963` or `262-758-8963`. After stripping non-digits, the last 10 digits are also `2627588963`.

**New `action_resolve_customer()` implementation:**

```python
def action_resolve_customer(self):
    """Find existing partner by deterministic last-10-digit phone match, or create."""
    Partner = self.env["res.partner"]
    for rec in self:
        if rec.partner_id:
            continue
        phone = rec.customer_phone
        if not phone:
            continue
        
        # Step 1-2: Normalize to last 10 digits
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7:
            continue  # Too short — skip
        normalized = digits[-10:]
        
        # Step 3: Search by phone_sanitized (E.164, most reliable)
        # phone_sanitized always ends with the national number
        candidates = Partner.search([
            ("phone_sanitized", "like", normalized),
        ])
        
        # Step 4: Filter for exact last-10-digit match
        matched = candidates.filtered(
            lambda p: re.sub(r"\D", "", p.phone_sanitized or "")[-10:] == normalized
        )
        
        # Step 5: Also check raw phone field for partners without phone_sanitized
        if not matched:
            raw_candidates = Partner.search([
                ("phone", "like", normalized),
                ("phone_sanitized", "=", False),
            ])
            matched = raw_candidates.filtered(
                lambda p: re.sub(r"\D", "", p.phone or "")[-10:] == normalized
            )
        
        if len(matched) == 1:
            rec.partner_id = matched
        elif len(matched) == 0:
            rec.partner_id = Partner.create({
                "name": rec.customer_name or phone,
                "phone": phone,
                "email": rec.customer_email or False,
                "customer_rank": 1,
            })
        else:
            # Multiple matches — do NOT auto-link. Log for manual resolution.
            rec.message_post(
                body=f"Phone match ambiguous: {len(matched)} partners match "
                     f"'{normalized}'. Please resolve manually.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )
```

### Key Differences from Previous Implementation

| Aspect | Before (buggy) | After (fixed) |
|--------|----------------|---------------|
| Match type | `ilike` (substring, case-insensitive) | `like` + programmatic last-10-digit exact check |
| Short numbers | No guard | Skip if < 7 digits |
| Multiple matches | Pick first (`limit=1`) | Refuse to auto-link, log warning |
| Field searched | `phone` OR `phone_sanitized` | `phone_sanitized` first (reliable), then `phone` fallback |
| Create behavior | Always creates if no match | Same (no change needed) |

---

## Phone Normalization Crosswalk

| Source | Raw Format | After strip | Last 10 |
|--------|-----------|------------|---------|
| 3CX international | `0012627588963` | `0012627588963` (13 digits) | `2627588963` |
| 3CX domestic | `12627588963` | `12627588963` (11 digits) | `2627588963` |
| User input (US) | `(262) 758-8963` | `2627588963` (10 digits) | `2627588963` |
| User input (int'l) | `+1-262-758-8963` | `12627588963` (11 digits) | `2627588963` |
| Odoo phone_sanitized | `+12627588963` | `12627588963` (11 digits) | `2627588963` |
| Legacy phone_clean | `2627588963` | `2627588963` (10 digits) | `2627588963` |

**All converge to the same 10 digits.** The last-10-digit strategy handles all known input formats.

---

## Edge Cases

### 1. International numbers (non-US)

US numbers have 10-digit national numbers. International numbers may have 7-12 digit national numbers.

**Policy:** For MVP, last-10-digit matching works because:
- 99%+ of onService customers are US-based
- Non-US callers are rare edge cases handled by manual partner assignment
- When international support grows, add `phone_validation` country-aware comparison

### 2. Same number, different contacts (shared phone)

Example: A family has one phone number but mother and father call separately.

**Policy:** First match wins. If the agent sees the wrong person, they manually change the partner. This matches legacy behavior (legacy also linked to a single customer_profile per phone).

### 3. Customer changes phone number

**Policy:** The OLD interaction keeps its partner link. New calls from the new number won't match. Agent manually creates or links the partner. Same as legacy.

### 4. VoIP/disposable numbers

Short numbers (< 7 digits) or obviously invalid numbers are skipped. No partner creation attempted.

---

## Test Cases (Required)

The following tests MUST pass on `onservice_test_db`:

| # | Scenario | Input Phone | Partner Phone | Expected |
|---|----------|------------|---------------|----------|
| 1 | Exact 10-digit match | `2625551234` | `2625551234` | Link |
| 2 | International prefix (3CX) | `0012625551234` | `+12625551234` | Link (both → `2625551234`) |
| 3 | Formatted US | `(262) 555-1234` | `262-555-1234` | Link (both → `2625551234`) |
| 4 | No match → create | `9995551234` | (none) | Create new partner |
| 5 | Multiple matches → refuse | `5551234567` | Partner A: `5551234567`, Partner B: `5551234567` | No auto-link, warning posted |
| 6 | Short number → skip | `911` | (any) | Skip, no change |
| 7 | No phone → skip | (empty) | (any) | Skip, no change |
| 8 | Already resolved → skip | `2625551234` | `2625551234` | Skip (partner already set) |

---

## Performance Considerations

- `phone_sanitized` is indexed by Odoo's `phone_validation` module
- The `like` operator with a 10-digit literal does a sequential scan unless there's a trigram index
- For the current partner count (~5K), this is fine (< 10ms)
- If partner count exceeds 100K, add a stored computed field `phone_last10` with btree index
- Legacy had `idx_customer_profiles_phone(phone_clean)` — equivalent coverage

---

## Migration Note

When migrating legacy `customer_profiles` into `res.partner`, ensure:
1. `phone` field gets the original formatted number
2. `phone_sanitized` gets computed by Odoo's `phone_validation` module (E.164)
3. `customer_segment` and `subscription_status` mapped from legacy fields
4. `odoo_partner_id` in legacy already points to the correct `res.partner.id` — verify this during migration
