# 16 — Migration Sequence

**Date:** 2026-04-01  
**Purpose:** Step-by-step plan for migrating from the onService middleware to Odoo, including data migration, feature parity gates, parallel running, and cutover criteria.  

---

## Migration Principles

1. **Parallel running** — Both systems run simultaneously until Odoo reaches parity
2. **No big bang** — Features migrate one domain at a time
3. **Always rollback-ready** — Middleware stays deployable throughout
4. **Data flows one direction** — Middleware → Odoo (never reverse-sync)
5. **Feature parity gate** — Each domain must pass acceptance before the next begins

---

## Phase Overview

```
Phase A: Foundation (Weeks 1-2)
  └── Core models, operations shell, roles

Phase B: Intake & CRM (Weeks 3-4)
  └── ons.interaction, crm.lead integration, customer search

Phase C: Cases & Sessions (Weeks 5-7)
  └── ons.case kanban, ons.session tracker, billing bridge

Phase D: Dispatch & 3CX (Weeks 8-10)
  └── ons.dispatch, 3CX collector daemon, queue monitoring

Phase E: AI & QA (Weeks 11-12)
  └── ons.qa.evaluation, OpenAI bridge, auto-grading

Phase F: Communications (Week 13)
  └── SMS bridge, email templates, notification routing

Phase G: Reports & Dashboards (Week 14)
  └── Dashboard widgets, graph views, KPI crons

Phase H: Data Migration & Cutover (Weeks 15-16)
  └── Historical data import, parallel validation, go-live
```

---

## Phase A: Foundation

### Modules Built
- `ons_ops_core` — Base models: `ons.call.driver`, shared mixins, config
- `ons_ops_shell` — Operations menu, home dashboard, role groups

### Data Migration
- None (new models, no historical data yet)

### Acceptance Gate
- [ ] Operations menu visible with correct role-based nav
- [ ] Home dashboard renders with placeholder widgets
- [ ] Three security groups created: Agent, Manager, Admin
- [ ] Config parameters for all integration keys created

---

## Phase B: Intake & CRM

### Modules Built
- `ons_ops_intake` — `ons.interaction` model, intake wizard
- `ons_ops_crm` — CRM lead automation, `res.partner` extensions

### Data Migration
```sql
-- Middleware → Odoo: customer_profiles → res.partner
INSERT INTO res_partner (name, phone, email, street, city, state_id, zip, ...)
SELECT
    COALESCE(first_name || ' ' || last_name, company_name),
    phone, email, address_line1, city,
    (SELECT id FROM res_country_state WHERE code = cp.state),
    zip, ...
FROM customer_profiles cp
WHERE NOT EXISTS (SELECT 1 FROM res_partner rp WHERE rp.phone = cp.phone);
```

```sql
-- Middleware → Odoo: submissions + call_logs → ons.interaction
-- Run via Python script using Odoo external API for proper ORM handling
```

### Parallel Running
- **Middleware:** Continues handling all live calls
- **Odoo:** 3CX daemon pushes new interactions to both systems
- **Duration:** 2 weeks minimum

### Acceptance Gate
- [ ] New intake form creates `ons.interaction` + `crm.lead`
- [ ] Customer search finds existing `res.partner` by phone/email
- [ ] Agent can classify interaction and set call driver
- [ ] Historical customers imported (count matches middleware ±5%)
- [ ] Recent interactions imported (last 90 days)

---

## Phase C: Cases & Sessions

### Modules Built
- `ons_ops_cases` — `ons.case`, `ons.case.stage`, `ons.session` models
- Billing bridge (ons_ops_billing — Stripe + Zoho controllers)

### Data Migration
```python
# cases → ons.case (Python migration script)
for case in middleware_cases:
    vals = {
        'name': case['case_number'],
        'partner_id': partner_map[case['customer_id']],
        'stage_id': stage_map[case['status']],
        'interaction_ids': [(4, interaction_map[sid]) for sid in case['submission_ids']],
        'description': case['notes'],
        'create_date': case['created_at'],
    }
    env['ons.case'].with_context(migration=True).create(vals)
```

### Acceptance Gate
- [ ] Case kanban board works with drag-drop stage changes
- [ ] Session tracker shows active sessions per agent
- [ ] Stripe payment intent created from session
- [ ] Stripe webhook creates `account.payment` linked to session
- [ ] Historical cases imported (last 6 months)

---

## Phase D: Dispatch & 3CX

### Modules Built
- `ons_ops_dispatch` — `ons.dispatch` model, WorkMarket bridge
- `ons_ops_3cx` — 3CX collector daemon, queue model

### Data Migration
```python
# workmarket_assignments → ons.dispatch
for wa in middleware_assignments:
    vals = {
        'case_id': case_map[wa['case_id']],
        'partner_id': partner_map[wa['customer_id']],
        'workmarket_id': wa['workmarket_assignment_id'],
        'state': state_map[wa['status']],
        'scheduled_date': wa['scheduled_date'],
        'technician_name': wa['technician_name'],
    }
    env['ons.dispatch'].with_context(migration=True).create(vals)
```

### Acceptance Gate
- [ ] Dispatch queue shows pending assignments
- [ ] Create dispatch → sends to WorkMarket API
- [ ] WorkMarket webhook updates dispatch state
- [ ] 3CX collector pushes active calls to Odoo
- [ ] Live calls view refreshes every 30 seconds
- [ ] Queue status widget on dashboard works

---

## Phase E: AI & QA

### Modules Built
- `ons_ops_ai` — OpenAI bridge, transcription queue, AI assist
- QA evaluation workflow in `ons_ops_core` (or dedicated `ons_ops_qa`)

### Data Migration
```python
# qa_evaluations → ons.qa.evaluation
for qa in middleware_qa:
    vals = {
        'interaction_id': interaction_map[qa['submission_id']],
        'agent_id': user_map[qa['agent_id']],
        'overall_score': qa['score'],
        'result': 'pass' if qa['passed'] else 'fail',
        'ai_transcript': qa['transcript'],
        'ai_feedback': qa['feedback'],
    }
    env['ons.qa.evaluation'].with_context(migration=True).create(vals)
```

### Acceptance Gate
- [ ] Recording triggers auto-transcription
- [ ] Transcription triggers auto-QA grading
- [ ] QA evaluation form shows score, breakdown, feedback
- [ ] Manager can override AI grade
- [ ] Agent can view their QA history
- [ ] Historical QA data imported (last 90 days)

---

## Phase F: Communications

### Modules Built
- `ons_ops_comms` — SMS bridge (Twilio), notification routing, templates

### Data Migration
- SMS templates from middleware → `mail.template` records
- No historical SMS data migration needed

### Acceptance Gate
- [ ] Send SMS from case/session context
- [ ] Inbound SMS creates `mail.message` on correct record
- [ ] Email templates for common notifications working
- [ ] Reminder system (scheduled actions) working

---

## Phase G: Reports & Dashboards

### Modules Built
- `ons_ops_reports` — Dashboard widgets, graph views, KPI crons
- Extends `ons_ops_shell` home dashboard with live data

### Data Migration
- None (reports compute from migrated data)

### Acceptance Gate
- [ ] Home dashboard shows live KPI counters
- [ ] My Performance page matches middleware metrics (±5%)
- [ ] Team Performance page matches middleware metrics (±5%)
- [ ] Call volume charts render correctly
- [ ] Revenue reports match Stripe/Zoho totals

---

## Phase H: Data Migration & Cutover

### Pre-Cutover Checklist
- [ ] All phases A-G acceptance gates passed
- [ ] 2-week parallel run with no critical issues
- [ ] All historical data imported and verified
- [ ] User training completed (all agents, managers)
- [ ] DNS/routing changes prepared but not applied
- [ ] Rollback plan tested

### Data Migration Execution Order

```
1. res.partner         (customer_profiles)     — prerequisite for all
2. ons.call.driver     (static reference data) — prerequisite for interactions
3. ons.interaction     (submissions+call_logs) — core entity
4. crm.lead            (derived from interactions)
5. ons.case + stages   (cases)
6. ons.session         (service_sessions)
7. ons.dispatch        (workmarket_assignments)
8. account.payment     (payment_transactions)
9. ons.qa.evaluation   (qa_evaluations)
10. mail.message       (notes, comments, activity log)
```

### Cutover Steps

```
Day -7:  Final full data migration rehearsal
Day -3:  Freeze middleware feature development
Day -1:  Final incremental data sync (delta since last migration)
Day  0:  
  06:00  Disable middleware login (maintenance page)
  06:15  Run final delta migration script
  06:30  Verify record counts match (±1%)
  06:45  Switch 3CX daemon to point at Odoo only
  07:00  Switch Stripe webhooks to Odoo endpoint
  07:00  Switch WorkMarket webhooks to Odoo endpoint
  07:15  Enable Odoo login for all users
  07:30  Monitor dashboards for 30 minutes
  08:00  Declare go-live or rollback
Day +1:  Keep middleware running (read-only) for reference
Day +7:  Decommission middleware if no issues
Day +30: Archive middleware codebase
```

### Rollback Plan

If critical issues within first 48 hours:
1. Re-enable middleware login
2. Switch 3CX daemon back to middleware
3. Switch webhooks back to middleware endpoints
4. Export any Odoo-only records created during cutover
5. Import those records into middleware
6. Declare rollback, schedule retry

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data loss during migration | HIGH | LOW | Dry-run migrations, record count verification |
| Feature gap discovered late | HIGH | MEDIUM | Acceptance gates at each phase |
| 3CX daemon instability | MEDIUM | LOW | PM2 auto-restart, health check endpoint |
| Stripe webhook downtime | HIGH | LOW | Queue missed events, replay from Stripe dashboard |
| User resistance | MEDIUM | MEDIUM | Training sessions, parallel running period |
| Odoo performance under load | MEDIUM | LOW | Stored compute fields, DB indexing |
| API rate limits (OpenAI, Twilio) | LOW | MEDIUM | Queue + backoff, configurable limits |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Data migration accuracy | ≥99% record match |
| Feature parity | 100% of acceptance gates |
| System uptime during cutover | ≥99.5% |
| Agent productivity (1 week post) | ≥90% of pre-migration |
| Agent productivity (4 weeks post) | ≥100% of pre-migration |
| Zero critical bugs | First 48 hours post-cutover |
