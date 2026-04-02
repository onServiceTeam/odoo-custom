#!/usr/bin/env python3
"""
load_demo_data.py — Realistic demo data loader for onService Operations.

Creates a complete vertical-slice scenario in the target database:
  - 10 customers (res.partner)
  - 10 interactions (ons.interaction)
  - 6 CRM leads (3 inquiry-only, 3 convertible)
  - 6 cases in various stages
  - Case lines / billing on 2 cases
  - 2 customer plans
  - 1 dispatch
  - Communication records

Usage:
  python3 scripts/load_demo_data.py [--db onservice_test_db]

Targets staging DB by default. Pass --db onservice_prod_db for production.
"""
import argparse
import xmlrpc.client
from datetime import datetime, timedelta

# ─── Connection ──────────────────────────────────────────────────────
URL = "http://127.0.0.1:8069"
MASTER_UID = 2
MASTER_PWD = "AuditCheck2026!"

def connect(db):
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(db, "admin@onservice.us", MASTER_PWD, {})
    assert uid, f"Authentication failed for {db}"
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    return uid, models

def x(models, db, uid, model, method, *args, **kw):
    """Shorthand for execute_kw."""
    return models.execute_kw(db, uid, MASTER_PWD, model, method, *args, **kw)

def ref(models, db, uid, xmlid):
    """Resolve an XML ID to a database ID."""
    module, name = xmlid.split(".")
    recs = x(models, db, uid, "ir.model.data", "search_read",
             [[["module","=",module],["name","=",name]]],
             {"fields": ["res_id"], "limit": 1})
    return recs[0]["res_id"] if recs else None

def find_stage(models, db, uid, code):
    ids = x(models, db, uid, "ons.case.stage", "search", [[["code","=",code]]])
    return ids[0] if ids else None

def find_dispatch_status(models, db, uid, code):
    ids = x(models, db, uid, "ons.dispatch.status", "search", [[["code","=",code]]])
    return ids[0] if ids else None

def find_driver(models, db, uid, code):
    ids = x(models, db, uid, "ons.call.driver", "search", [[["code","=",code]]])
    return ids[0] if ids else None

def find_product(models, db, uid, code):
    ids = x(models, db, uid, "product.template", "search", [[["ons_product_code","=",code]]])
    if ids:
        # Get product.product for the template
        pp = x(models, db, uid, "product.product", "search", [[["product_tmpl_id","=",ids[0]]]])
        return pp[0] if pp else None
    return None

# ─── Main ────────────────────────────────────────────────────────────
def load(db):
    uid, m = connect(db)
    print(f"Connected to {db} as uid={uid}")

    # ── Helpers ──────────────────────────────────────────────────────
    now = datetime.now()
    def ts(days_ago=0, hours_ago=0):
        dt = now - timedelta(days=days_ago, hours=hours_ago)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # ── 1. CUSTOMERS ────────────────────────────────────────────────
    print("\n── Creating customers ──")
    customers = [
        {"name": "Martha Rodriguez", "phone": "+1 (305) 555-0142", "email": "martha.rodriguez@email.com",
         "street": "1245 Coral Way", "city": "Miami", "zip": "33145",
         "customer_segment": "returning", "company_type": "person"},
        {"name": "James Patterson", "phone": "+1 (404) 555-0198", "email": "james.p@techcorp.com",
         "street": "880 Peachtree St NE", "city": "Atlanta", "zip": "30309",
         "customer_segment": "subscriber", "company_type": "person"},
        {"name": "Linda Chen", "phone": "+1 (212) 555-0167", "email": "linda.chen@outlook.com",
         "street": "350 Fifth Avenue", "city": "New York", "zip": "10118",
         "customer_segment": "new", "company_type": "person"},
        {"name": "Robert Williams", "phone": "+1 (713) 555-0123", "email": "rwilliams@gmail.com",
         "street": "6900 Fannin St", "city": "Houston", "zip": "77030",
         "customer_segment": "returning", "company_type": "person"},
        {"name": "Sarah Mitchell", "phone": "+1 (602) 555-0156", "email": "sarah.m@desertair.com",
         "street": "2901 N Central Ave", "city": "Phoenix", "zip": "85012",
         "customer_segment": "new", "company_type": "person"},
        {"name": "David Thompson", "phone": "+1 (312) 555-0189", "email": "dthompson@chicagolaw.com",
         "street": "200 E Randolph St", "city": "Chicago", "zip": "60601",
         "customer_segment": "vip", "company_type": "person"},
        {"name": "TechStart Solutions LLC", "phone": "+1 (415) 555-0134", "email": "support@techstart.io",
         "street": "1 Market St", "city": "San Francisco", "zip": "94105",
         "customer_segment": "subscriber", "company_type": "company",
         "is_company": True},
        {"name": "Angela Foster", "phone": "+1 (214) 555-0177", "email": "angela.foster@yahoo.com",
         "street": "3939 McKinney Ave", "city": "Dallas", "zip": "75204",
         "customer_segment": "new", "company_type": "person"},
        {"name": "Michael Brooks", "phone": "+1 (206) 555-0112", "email": "mbrooks@seattledesign.com",
         "street": "400 Broad St", "city": "Seattle", "zip": "98109",
         "customer_segment": "returning", "company_type": "person"},
        {"name": "Patricia Gomez", "phone": "+1 (954) 555-0145", "email": "pgomez@comcast.net",
         "street": "110 E Broward Blvd", "city": "Fort Lauderdale", "zip": "33301",
         "customer_segment": "new", "company_type": "person"},
    ]

    partner_ids = {}
    for c in customers:
        # Check if exists first
        existing = x(m, db, uid, "res.partner", "search", [[["email","=",c["email"]]]])
        if existing:
            partner_ids[c["name"]] = existing[0]
            print(f"  ↳ {c['name']} already exists (id={existing[0]})")
        else:
            pid = x(m, db, uid, "res.partner", "create", [c])
            partner_ids[c["name"]] = pid
            print(f"  ✓ {c['name']} (id={pid})")

    # ── 2. INTERACTIONS ─────────────────────────────────────────────
    print("\n── Creating interactions ──")
    drv_popup = find_driver(m, db, uid, "HACKED_POPUP_SCAM")
    drv_slow = find_driver(m, db, uid, "PERF_SLOW_GENERAL")
    drv_noos = find_driver(m, db, uid, "BOOT_NO_OS")
    drv_printer = find_driver(m, db, uid, "PRINTER_OFFLINE")
    drv_bsod = find_driver(m, db, uid, "BOOT_BLUE_SCREEN")
    drv_noint = find_driver(m, db, uid, "NET_NO_INTERNET_SINGLE_DEVICE")
    drv_billing = find_driver(m, db, uid, "BILLING_QUESTION")
    drv_remote = find_driver(m, db, uid, "HACKED_REMOTE_CONTROL")
    drv_freeze = find_driver(m, db, uid, "PERF_FREEZING_LOCKUPS")
    drv_email = find_driver(m, db, uid, "EMAIL_OUTLOOK_NOT_OPENING")

    interactions_data = [
        # 1. Martha — popup scam, urgent, converted to case
        {"partner_id": partner_ids["Martha Rodriguez"],
         "customer_name": "Martha Rodriguez", "customer_phone": "+1 (305) 555-0142",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_popup, "urgency": "high",
         "session_path": "session_now",
         "issue_description": "Customer reports threatening popup claiming computer is infected. Cannot close browser. Very panicked — worried about bank accounts.",
         "call_duration": 480, "talk_duration": 420,
         "caller_type": "returning", "customer_type": "home",
         "create_date": ts(days_ago=3, hours_ago=2)},
        # 2. James — slow computer, subscriber follow-up
        {"partner_id": partner_ids["James Patterson"],
         "customer_name": "James Patterson", "customer_phone": "+1 (404) 555-0198",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_slow, "urgency": "medium",
         "session_path": "session_now",
         "issue_description": "Computer very slow after Windows update. Takes 10 minutes to boot. Has 1-year support plan — calling to use it.",
         "call_duration": 360, "talk_duration": 300,
         "caller_type": "subscriber", "customer_type": "home",
         "create_date": ts(days_ago=2, hours_ago=6)},
        # 3. Linda — no OS, needs callback
        {"partner_id": partner_ids["Linda Chen"],
         "customer_name": "Linda Chen", "customer_phone": "+1 (212) 555-0167",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_noos, "urgency": "high",
         "session_path": "callback",
         "issue_description": "Computer shows 'No bootable device found'. Customer has important work files — very worried about data loss. Requested callback for tomorrow morning.",
         "call_duration": 600, "talk_duration": 540,
         "caller_type": "new", "customer_type": "home",
         "create_date": ts(days_ago=2, hours_ago=1)},
        # 4. Robert — printer offline, inquiry only
        {"partner_id": partner_ids["Robert Williams"],
         "customer_name": "Robert Williams", "customer_phone": "+1 (713) 555-0123",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_printer, "urgency": "low",
         "session_path": "no_session",
         "issue_description": "Asking about pricing for printer setup help. Has a new HP LaserJet that won't connect to WiFi. Will call back after discussing with spouse.",
         "call_duration": 180, "talk_duration": 160,
         "caller_type": "new", "customer_type": "home",
         "create_date": ts(days_ago=1, hours_ago=5)},
        # 5. Sarah — BSOD, needs onsite
        {"partner_id": partner_ids["Sarah Mitchell"],
         "customer_name": "Sarah Mitchell", "customer_phone": "+1 (602) 555-0156",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_bsod, "urgency": "high",
         "session_path": "onsite_queue",
         "issue_description": "Repeated blue screen errors — IRQL_NOT_LESS_OR_EQUAL. Desktop PC, 3 years old. Customer cannot bring to office — needs onsite technician.",
         "call_duration": 540, "talk_duration": 480,
         "caller_type": "new", "customer_type": "home",
         "create_date": ts(days_ago=1, hours_ago=3)},
        # 6. David — no internet, VIP
        {"partner_id": partner_ids["David Thompson"],
         "customer_name": "David Thompson", "customer_phone": "+1 (312) 555-0189",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Priority Queue",
         "primary_driver_id": drv_noint, "urgency": "medium",
         "session_path": "session_now",
         "issue_description": "VIP client — law office. One workstation lost internet after firmware update on router. Other devices fine. Needs quick fix.",
         "call_duration": 300, "talk_duration": 270,
         "caller_type": "returning", "customer_type": "business",
         "create_date": ts(days_ago=1, hours_ago=1)},
        # 7. TechStart — billing question, inquiry only
        {"partner_id": partner_ids["TechStart Solutions LLC"],
         "customer_name": "TechStart Solutions LLC", "customer_phone": "+1 (415) 555-0134",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_billing, "urgency": "low",
         "session_path": "no_session",
         "issue_description": "Existing subscriber asking about upgrading from 6-month plan to 1-year plan. Wants pricing difference and whether remaining months carry over.",
         "call_duration": 240, "talk_duration": 200,
         "caller_type": "subscriber", "customer_type": "business",
         "create_date": ts(days_ago=1)},
        # 8. Angela — remote control/hack, urgent
        {"partner_id": partner_ids["Angela Foster"],
         "customer_name": "Angela Foster", "customer_phone": "+1 (214) 555-0177",
         "interaction_type": "phone", "direction": "inbound",
         "state": "completed", "queue_name": "Main Queue",
         "primary_driver_id": drv_remote, "urgency": "high",
         "session_path": "session_now",
         "issue_description": "Customer let someone from a 'Microsoft support' call remote into her PC. They installed software and asked for payment. Customer panicking — worried about identity theft and bank access.",
         "call_duration": 900, "talk_duration": 840,
         "caller_type": "new", "customer_type": "home",
         "create_date": ts(hours_ago=6)},
        # 9. Michael — freezing, returning customer
        {"partner_id": partner_ids["Michael Brooks"],
         "customer_name": "Michael Brooks", "customer_phone": "+1 (206) 555-0112",
         "interaction_type": "phone", "direction": "inbound",
         "state": "classified", "queue_name": "Main Queue",
         "primary_driver_id": drv_freeze, "urgency": "medium",
         "session_path": "session_now",
         "issue_description": "Laptop freezes every 20 minutes. Has to force restart. Happening for 2 weeks. Returning customer — we fixed his email last year.",
         "call_duration": 420, "talk_duration": 360,
         "caller_type": "returning", "customer_type": "home",
         "create_date": ts(hours_ago=3)},
        # 10. Patricia — Outlook, inquiry
        {"partner_id": partner_ids["Patricia Gomez"],
         "customer_name": "Patricia Gomez", "customer_phone": "+1 (954) 555-0145",
         "interaction_type": "email", "direction": "inbound",
         "state": "classified", "queue_name": "Email Queue",
         "primary_driver_id": drv_email, "urgency": "low",
         "session_path": "no_session",
         "issue_description": "Email inquiry: Outlook stopped opening after Windows update. Getting error about profile. Asking if this is something we can help with and pricing.",
         "caller_type": "new", "customer_type": "home",
         "create_date": ts(hours_ago=1)},
    ]

    interaction_ids = {}
    for i, data in enumerate(interactions_data):
        cname = data["customer_name"]
        iid = x(m, db, uid, "ons.interaction", "create", [data])
        interaction_ids[cname] = iid
        print(f"  ✓ INT #{i+1}: {cname} — {data['primary_driver_id']} (id={iid})")

    # ── 3. CRM LEADS ────────────────────────────────────────────────
    print("\n── Creating CRM leads ──")

    # 3 inquiry-only leads (won't convert to cases)
    inquiry_leads = [
        {"name": "Robert Williams — Printer Setup Inquiry",
         "partner_id": partner_ids["Robert Williams"],
         "phone": "+1 (713) 555-0123",
         "email_from": "rwilliams@gmail.com",
         "type": "lead",
         "interaction_id": interaction_ids["Robert Williams"],
         "description": "Pricing inquiry for printer WiFi setup. Will call back."},
        {"name": "TechStart Solutions — Plan Upgrade Inquiry",
         "partner_id": partner_ids["TechStart Solutions LLC"],
         "phone": "+1 (415) 555-0134",
         "email_from": "support@techstart.io",
         "type": "lead",
         "interaction_id": interaction_ids["TechStart Solutions LLC"],
         "description": "Existing subscriber asking about upgrading plan term."},
        {"name": "Patricia Gomez — Outlook Issue Inquiry",
         "partner_id": partner_ids["Patricia Gomez"],
         "phone": "+1 (954) 555-0145",
         "email_from": "pgomez@comcast.net",
         "type": "lead",
         "interaction_id": interaction_ids["Patricia Gomez"],
         "description": "Email inquiry about Outlook not opening. Asking about pricing."},
    ]

    lead_ids = {}
    for ld in inquiry_leads:
        lid = x(m, db, uid, "crm.lead", "create", [ld])
        lead_ids[ld["name"]] = lid
        print(f"  ✓ Lead (inquiry): {ld['name'][:50]}… (id={lid})")

    # 3 convertible leads — these will become cases
    convert_leads = [
        {"name": "Michael Brooks — Laptop Freezing",
         "partner_id": partner_ids["Michael Brooks"],
         "phone": "+1 (206) 555-0112",
         "email_from": "mbrooks@seattledesign.com",
         "type": "opportunity",
         "interaction_id": interaction_ids["Michael Brooks"],
         "description": "Returning customer. Laptop freezing every 20 min. Ready for session."},
        {"name": "Angela Foster — Remote Hack Recovery",
         "partner_id": partner_ids["Angela Foster"],
         "phone": "+1 (214) 555-0177",
         "email_from": "angela.foster@yahoo.com",
         "type": "opportunity",
         "interaction_id": interaction_ids["Angela Foster"],
         "description": "URGENT: Customer was remotely accessed by scammer. Full malware removal and bank security needed."},
        {"name": "Sarah Mitchell — BSOD Onsite Needed",
         "partner_id": partner_ids["Sarah Mitchell"],
         "phone": "+1 (602) 555-0156",
         "email_from": "sarah.m@desertair.com",
         "type": "opportunity",
         "interaction_id": interaction_ids["Sarah Mitchell"],
         "description": "Repeated BSOD. Needs onsite technician — cannot transport desktop."},
    ]

    for ld in convert_leads:
        lid = x(m, db, uid, "crm.lead", "create", [ld])
        lead_ids[ld["name"]] = lid
        print(f"  ✓ Lead (convertible): {ld['name'][:50]}… (id={lid})")

    # ── 4. CASES ────────────────────────────────────────────────────
    print("\n── Creating cases ──")
    stage = lambda code: find_stage(m, db, uid, code)

    # We create cases directly via SQL-level create (bypass transition
    # validation) by setting the initial stage and then advancing.
    # Actually the ORM create sets intake_submitted, then we advance.

    cases_data = [
        # Case 1: Martha — Popup scam — in repair_in_progress (stage 6)
        {"partner_id": partner_ids["Martha Rodriguez"],
         "source_interaction_id": interaction_ids["Martha Rodriguez"],
         "primary_driver_id": drv_popup,
         "issue_description": "Threatening popup scam. Browser hijacked. Customer worried about bank accounts. Removed malware, running full scan now.",
         "session_path": "session_now",
         "intake_agent_id": uid,
         "assigned_tech_id": uid,
         "target_stage": "repair_in_progress"},
        # Case 2: James — Slow computer — billing_in_progress (stage 8)
        {"partner_id": partner_ids["James Patterson"],
         "source_interaction_id": interaction_ids["James Patterson"],
         "primary_driver_id": drv_slow,
         "issue_description": "Slow after Windows update. Disabled startup bloat, cleared temp files, optimized services. Ready for billing — subscriber with plan.",
         "session_path": "session_now",
         "intake_agent_id": uid,
         "assigned_tech_id": uid,
         "billing_agent_id": uid,
         "target_stage": "billing_in_progress"},
        # Case 3: Linda — No OS / callback — callback_scheduled (stage 3)
        {"partner_id": partner_ids["Linda Chen"],
         "source_interaction_id": interaction_ids["Linda Chen"],
         "primary_driver_id": drv_noos,
         "issue_description": "No bootable device. Customer has work files. Scheduled callback for tomorrow 9 AM to begin remote diagnostics.",
         "session_path": "callback",
         "intake_agent_id": uid,
         "target_stage": "callback_scheduled"},
        # Case 4: David — No internet — closed_won (stage 10)
        {"partner_id": partner_ids["David Thompson"],
         "source_interaction_id": interaction_ids["David Thompson"],
         "primary_driver_id": drv_noint,
         "issue_description": "Single device lost internet after router firmware update. Reset network adapter, flushed DNS, reconnected. Resolved in 15 minutes. VIP client — law office.",
         "session_path": "session_now",
         "intake_agent_id": uid,
         "assigned_tech_id": uid,
         "billing_agent_id": uid,
         "target_stage": "closed_won"},
        # Case 5: Angela — Remote hack — online_session_started (stage 4)
        {"partner_id": partner_ids["Angela Foster"],
         "source_interaction_id": interaction_ids["Angela Foster"],
         "primary_driver_id": drv_remote,
         "issue_description": "CRITICAL: Customer gave remote access to scammer. Disconnected internet immediately. Starting full malware removal and credential reset.",
         "session_path": "session_now",
         "intake_agent_id": uid,
         "assigned_tech_id": uid,
         "target_stage": "online_session_started"},
        # Case 6: Sarah — BSOD / onsite — onsite_dispatched (stage 12)
        {"partner_id": partner_ids["Sarah Mitchell"],
         "source_interaction_id": interaction_ids["Sarah Mitchell"],
         "primary_driver_id": drv_bsod,
         "issue_description": "BSOD (IRQL_NOT_LESS_OR_EQUAL). Desktop PC, 3 years old. Customer cannot transport. Dispatching onsite technician.",
         "session_path": "onsite_queue",
         "intake_agent_id": uid,
         "target_stage": "onsite_dispatched"},
    ]

    # Stage progression paths for each case
    STAGE_PATHS = {
        "repair_in_progress": [
            "intake_submitted", "triage_in_progress",
            "online_session_started", "handoff_to_assisting",
            "repair_in_progress"],
        "billing_in_progress": [
            "intake_submitted", "triage_in_progress",
            "online_session_started", "repair_in_progress",
            "ready_for_verification", "billing_in_progress"],
        "callback_scheduled": [
            "intake_submitted", "callback_scheduled"],
        "closed_won": [
            "intake_submitted", "triage_in_progress",
            "online_session_started", "repair_in_progress",
            "ready_for_verification", "billing_in_progress",
            "paid", "closed_won"],
        "online_session_started": [
            "intake_submitted", "online_session_started"],
        "onsite_dispatched": [
            "intake_submitted", "onsite_dispatched"],
    }

    case_ids = {}
    for cd in cases_data:
        target = cd.pop("target_stage")
        path = STAGE_PATHS[target]

        # Create case (starts at intake_submitted)
        create_vals = {k: v for k, v in cd.items() if k != "session_path"}
        create_vals["stage_id"] = stage(path[0])
        cid = x(m, db, uid, "ons.case", "create", [create_vals])
        cname = x(m, db, uid, "ons.case", "read", [[cid]], {"fields": ["name"]})[0]["name"]

        # Advance through stages
        for next_code in path[1:]:
            x(m, db, uid, "ons.case", "write", [[cid], {"stage_id": stage(next_code)}])

        partner_name = [c["name"] for c in customers if partner_ids[c["name"]] == cd["partner_id"]][0]
        case_ids[partner_name] = cid
        print(f"  ✓ {cname}: {partner_name} → {target} (id={cid})")

    # ── 5. CASE LINES / BILLING ────────────────────────────────────
    print("\n── Adding billing lines ──")

    # James (billing_in_progress) — Standard Fix + Browser Guard
    prod_standard = find_product(m, db, uid, "STANDARD_FIX")
    prod_browser = find_product(m, db, uid, "BROWSER_GUARD")
    if prod_standard and case_ids.get("James Patterson"):
        x(m, db, uid, "ons.case.line", "create", [{
            "case_id": case_ids["James Patterson"],
            "product_id": prod_standard,
            "quantity": 1,
            "unit_price": 129.99,
            "description": "Standard Fix — Windows optimization post-update",
        }])
        print(f"  ✓ James: Standard Fix $129.99")
    if prod_browser and case_ids.get("James Patterson"):
        x(m, db, uid, "ons.case.line", "create", [{
            "case_id": case_ids["James Patterson"],
            "product_id": prod_browser,
            "quantity": 1,
            "unit_price": 49.99,
            "description": "Browser Guard add-on",
        }])
        print(f"  ✓ James: Browser Guard $49.99")

    # David (closed_won) — Quick Fix (VIP, resolved fast)
    prod_quick = find_product(m, db, uid, "QUICK_FIX")
    if prod_quick and case_ids.get("David Thompson"):
        x(m, db, uid, "ons.case.line", "create", [{
            "case_id": case_ids["David Thompson"],
            "product_id": prod_quick,
            "quantity": 1,
            "unit_price": 49.99,
            "description": "Quick Fix — network adapter reset",
        }])
        # Mark as paid
        x(m, db, uid, "ons.case", "write", [[case_ids["David Thompson"]], {
            "payment_status": "paid",
            "payment_amount": 49.99,
        }])
        print(f"  ✓ David: Quick Fix $49.99 — PAID")

    # ── 6. CUSTOMER PLANS ───────────────────────────────────────────
    print("\n── Creating customer plans ──")

    prod_plan_1yr = find_product(m, db, uid, "PLAN_1YR")
    prod_plan_6mo = find_product(m, db, uid, "PLAN_6MO")

    if prod_plan_1yr:
        plan1 = x(m, db, uid, "ons.customer.plan", "create", [{
            "partner_id": partner_ids["James Patterson"],
            "product_id": prod_plan_1yr,
            "amount": 349.99,
            "term_months": 12,
            "start_date": (now - timedelta(days=90)).strftime("%Y-%m-%d"),
            "state": "active",
        }])
        print(f"  ✓ James Patterson: 1-Year Plan $349.99 (active, id={plan1})")

    if prod_plan_6mo:
        plan2 = x(m, db, uid, "ons.customer.plan", "create", [{
            "partner_id": partner_ids["TechStart Solutions LLC"],
            "product_id": prod_plan_6mo,
            "amount": 249.99,
            "term_months": 6,
            "start_date": (now - timedelta(days=150)).strftime("%Y-%m-%d"),
            "state": "expiring_soon",
        }])
        print(f"  ✓ TechStart: 6-Month Plan $249.99 (expiring_soon, id={plan2})")

    # ── 7. DISPATCH ─────────────────────────────────────────────────
    print("\n── Creating dispatch ──")
    ds_assigned = find_dispatch_status(m, db, uid, "assigned")
    if ds_assigned and case_ids.get("Sarah Mitchell"):
        disp = x(m, db, uid, "ons.dispatch", "create", [{
            "title": "BSOD Repair — Desktop PC Onsite",
            "description": "Customer experiencing repeated BSOD (IRQL_NOT_LESS_OR_EQUAL). 3-year-old desktop. Cannot transport. Full hardware diagnostics and driver repair needed.",
            "case_id": case_ids["Sarah Mitchell"],
            "partner_id": partner_ids["Sarah Mitchell"],
            "status_id": find_dispatch_status(m, db, uid, "draft"),
            "location_type": "residential",
            "street": "2901 N Central Ave",
            "city": "Phoenix",
            "zip": "85012",
            "contact_first_name": "Sarah",
            "contact_last_name": "Mitchell",
            "contact_phone": "+1 (602) 555-0156",
            "budget": 199.99,
            "scheduled_start": (now + timedelta(days=1, hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduled_end": (now + timedelta(days=1, hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
            "special_instructions": "Ring doorbell twice. Small white dog — not aggressive. Garage has the desktop PC.",
        }])
        dname = x(m, db, uid, "ons.dispatch", "read", [[disp]], {"fields": ["name"]})[0]["name"]
        print(f"  ✓ {dname}: Sarah Mitchell BSOD onsite (id={disp})")

        # Advance to assigned via allowed transitions: draft → pending_approval → sent → assigned
        for next_status in ["pending_approval", "sent", "assigned"]:
            sid = find_dispatch_status(m, db, uid, next_status)
            x(m, db, uid, "ons.dispatch", "write", [[disp], {"status_id": sid}])
        print(f"  ✓ Dispatch advanced to 'assigned'")

    # ── 8. CONSENT RECORDS ──────────────────────────────────────────
    print("\n── Creating consent records ──")
    consents = [
        {"partner_id": partner_ids["Martha Rodriguez"], "channel": "phone", "scope": "service_terms",
         "status": "opted_in", "capture_source": "phone_call"},
        {"partner_id": partner_ids["James Patterson"], "channel": "any", "scope": "service_terms",
         "status": "opted_in", "capture_source": "phone_call"},
        {"partner_id": partner_ids["James Patterson"], "channel": "email", "scope": "renewal",
         "status": "opted_in", "capture_source": "phone_call"},
        {"partner_id": partner_ids["David Thompson"], "channel": "phone", "scope": "service_terms",
         "status": "opted_in", "capture_source": "phone_call"},
        {"partner_id": partner_ids["Angela Foster"], "channel": "phone", "scope": "service_terms",
         "status": "opted_in", "capture_source": "phone_call"},
    ]
    for con in consents:
        # Check for existing
        existing = x(m, db, uid, "ons.contact.consent", "search", [
            [["partner_id","=",con["partner_id"]],
             ["channel","=",con["channel"]],
             ["scope","=",con["scope"]]]])
        if not existing:
            cid = x(m, db, uid, "ons.contact.consent", "create", [con])
            print(f"  ✓ Consent: partner {con['partner_id']} {con['channel']}/{con['scope']} (id={cid})")
        else:
            print(f"  ↳ Consent already exists for partner {con['partner_id']}")

    # ── SUMMARY ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DEMO DATA LOAD COMPLETE")
    print("=" * 60)
    int_count = x(m, db, uid, "ons.interaction", "search_count", [[]])
    lead_count = x(m, db, uid, "crm.lead", "search_count", [[]])
    case_count = x(m, db, uid, "ons.case", "search_count", [[]])
    plan_count = x(m, db, uid, "ons.customer.plan", "search_count", [[]])
    disp_count = x(m, db, uid, "ons.dispatch", "search_count", [[]])
    consent_count = x(m, db, uid, "ons.contact.consent", "search_count", [[]])
    print(f"  Interactions:  {int_count}")
    print(f"  CRM Leads:     {lead_count}")
    print(f"  Cases:         {case_count}")
    print(f"  Customer Plans:{plan_count}")
    print(f"  Dispatches:    {disp_count}")
    print(f"  Consents:      {consent_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="onservice_test_db",
                        help="Target database (default: onservice_test_db)")
    args = parser.parse_args()
    load(args.db)
