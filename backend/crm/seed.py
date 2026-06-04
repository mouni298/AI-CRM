"""Synthetic CRM seed — deterministic, no random/time dependencies.

Populates one SaaS company's CRM ("Acme Analytics", a product-analytics tool):
accounts, contacts, deals, activities, inbound leads, support tickets, and a KB.

The data is hand-tuned so the eval harness has known-correct outcomes:
  - some tickets are answerable from the KB (deflectable), some are not (escalate);
  - some leads are clean ICP fits (qualify+route), some clear no's (disqualify),
    some ambiguous (low-confidence handoff).
See backend/eval/fixtures/ for the labels.

Run:  python -m backend.crm.seed         (seeds data/crm.db)
"""

from __future__ import annotations

from .base import Account, Activity, Contact, Deal, KBArticle, Lead, Ticket
from .sqlite_store import SqliteStore

# --------------------------------------------------------------------------- #
# Accounts + contacts (the researcher/outreach flow reads these)
# --------------------------------------------------------------------------- #
ACCOUNTS = [
    Account("acc-001", "Northwind Trading", "ecommerce", "mid", "US-East", "ok"),
    Account("acc-002", "Globex Fintech", "fintech", "enterprise", "US-West", "at_risk"),
    Account("acc-003", "Initech SaaS", "saas", "mid", "EU", "ok"),
    Account("acc-004", "Hooli Media", "media", "enterprise", "US-West", "churning"),
    Account("acc-005", "Soylent Foods", "cpg", "smb", "US-Central", "ok"),
    Account("acc-006", "Umbrella Health", "healthcare", "enterprise", "EU", "ok"),
]

CONTACTS = [
    Contact("con-001", "acc-001", "Dana Reyes", "VP Growth", "dana@northwind.example"),
    Contact("con-002", "acc-001", "Sam Okoro", "Data Analyst", "sam@northwind.example"),
    Contact("con-003", "acc-002", "Priya Nair", "Director of Ops", "priya@globex.example"),
    Contact("con-004", "acc-003", "Lukas Berg", "Head of Product", "lukas@initech.example"),
    Contact("con-005", "acc-004", "Mei Tanaka", "CMO", "mei@hooli.example"),
    Contact("con-006", "acc-006", "Omar Haddad", "Eng Manager", "omar@umbrella.example"),
]

DEALS = [
    Deal("deal-001", "acc-001", "Northwind — Growth tier expansion", "negotiation", 48000, "rep:alex", 4),
    Deal("deal-002", "acc-002", "Globex — Enterprise renewal", "proposal", 220000, "rep:jordan", 21),
    Deal("deal-003", "acc-003", "Initech — Mid tier upsell", "qualification", 36000, "rep:alex", 9),
    Deal("deal-004", "acc-004", "Hooli — Renewal at risk", "negotiation", 180000, "rep:jordan", 47),
    Deal("deal-005", "acc-006", "Umbrella — New logo", "prospecting", 95000, "rep:sam", 2),
]

ACTIVITIES = [
    Activity("act-001", "acc-001", "con-001", "meeting", "Demo of cohort-retention dashboards; Dana liked funnels.", 6),
    Activity("act-002", "acc-001", "con-002", "email", "Sam asked about CSV export limits on large reports.", 3),
    Activity("act-003", "acc-001", "con-001", "call", "Discussed Growth tier pricing and added-seat costs.", 2),
    Activity("act-004", "acc-002", "con-003", "meeting", "QBR — Globex flagged slow dashboards on big datasets.", 14),
    Activity("act-005", "acc-002", "con-003", "note", "Renewal risk: exec sponsor left; new sponsor TBD.", 10),
    Activity("act-006", "acc-003", "con-004", "email", "Lukas requested SSO/SAML rollout timeline.", 5),
    Activity("act-007", "acc-004", "con-005", "call", "Hooli considering competitor; usage down 40% QoQ.", 8),
    Activity("act-008", "acc-006", "con-006", "meeting", "Security review; Umbrella needs data-retention details.", 1),
]

# --------------------------------------------------------------------------- #
# Knowledge base (RAG ingestion source — backs the deflection agent)
# --------------------------------------------------------------------------- #
KB = [
    KBArticle("kb-001", "Resetting your password",
        "To reset your password, click 'Forgot password' on the sign-in page and "
        "enter your account email. You'll receive a reset link valid for 60 minutes. "
        "If the email doesn't arrive, check spam or contact your workspace admin, who "
        "can trigger a reset from Settings > Members.", ["account", "auth"]),
    KBArticle("kb-002", "Inviting team members and managing seats",
        "Workspace admins invite members under Settings > Members > Invite. Each "
        "invited member consumes one seat on your plan. The Growth plan includes 10 "
        "seats; additional seats are $12/seat/month. Pending invites don't consume a "
        "seat until accepted.", ["billing", "seats", "admin"]),
    KBArticle("kb-003", "Exporting reports to CSV",
        "Open any report and choose Export > CSV. Exports are capped at 1,000,000 "
        "rows per file; larger reports are split into multiple files automatically. "
        "Scheduled CSV exports can be configured under Report > Schedule on Growth and "
        "Enterprise plans.", ["reports", "export"]),
    KBArticle("kb-004", "API rate limits",
        "The REST API allows 600 requests per minute per workspace on Growth and "
        "1,200 on Enterprise. Exceeding the limit returns HTTP 429 with a Retry-After "
        "header. Use exponential backoff. Bulk endpoints count as one request per 100 "
        "records.", ["api", "limits"]),
    KBArticle("kb-005", "Connecting a data source",
        "Go to Settings > Data Sources > Connect. We support Postgres, BigQuery, "
        "Snowflake, and Segment. Connections sync every 15 minutes on Growth and every "
        "5 minutes on Enterprise. A failed sync retries 3 times before alerting the "
        "workspace admin.", ["integrations", "data"]),
    KBArticle("kb-006", "Billing cycle and invoices",
        "Billing runs monthly on the date you first subscribed. Invoices are emailed "
        "to the billing contact and available under Settings > Billing > Invoices. We "
        "accept credit card and, on Enterprise, ACH/wire. Annual plans are billed "
        "upfront with a 2-month discount.", ["billing", "invoices"]),
    KBArticle("kb-007", "Upgrading or downgrading your plan",
        "Change plans under Settings > Billing > Plan. Upgrades take effect "
        "immediately and are prorated. Downgrades take effect at the end of the "
        "current billing period; you keep current features until then. Downgrading "
        "below your current seat count requires removing members first.", ["billing", "plans"]),
    KBArticle("kb-008", "Setting up two-factor authentication",
        "Enable 2FA under Settings > Security > Two-Factor. We support authenticator "
        "apps (TOTP) and SMS. Admins can require 2FA for all members. Recovery codes "
        "are shown once at setup — store them safely; lost codes require admin "
        "reset.", ["auth", "security"]),
    KBArticle("kb-009", "Data retention policy",
        "Event data is retained for 25 months on Growth and 50 months on Enterprise. "
        "Deleted reports are recoverable from Trash for 30 days. On account closure, "
        "data is purged within 90 days. Custom retention windows are available on "
        "Enterprise contracts.", ["data", "compliance"]),
    KBArticle("kb-010", "Configuring SSO / SAML",
        "SSO via SAML 2.0 is available on Enterprise. Configure it under Settings > "
        "Security > SSO with your IdP metadata URL. We support Okta, Entra ID, and "
        "Google Workspace. SCIM user provisioning is available on request. Test in a "
        "staging connection before enforcing org-wide.", ["auth", "sso", "enterprise"]),
    KBArticle("kb-011", "Setting up webhooks",
        "Create webhooks under Settings > Developers > Webhooks. We POST a JSON "
        "payload on the events you subscribe to and expect a 2xx within 5 seconds. "
        "Failed deliveries retry with backoff for up to 24 hours. Each payload is "
        "signed with an HMAC header for verification.", ["api", "webhooks", "developers"]),
    KBArticle("kb-012", "Dashboard sharing and permissions",
        "Share a dashboard via Share > Invite or a public link. Roles are Viewer, "
        "Editor, and Admin. Public links can be password-protected and expire on a "
        "set date. Row-level permissions on shared dashboards are an Enterprise "
        "feature.", ["sharing", "permissions"]),
]

# --------------------------------------------------------------------------- #
# Support tickets (deflection flow). resolved_by/status left at defaults so the
# agent's run is meaningful. Eval labels mark which are KB-deflectable.
# --------------------------------------------------------------------------- #
TICKETS = [
    Ticket("tic-001", "acc-001", "con-002", "Can't export my large report",
        "My report has ~2 million rows and the CSV export seems to stop. How do I get all of it?", "normal"),
    Ticket("tic-002", "acc-003", "con-004", "How do I add more people to our workspace?",
        "We hired 3 analysts. How do I give them access and what does it cost?", "normal"),
    Ticket("tic-003", "acc-001", "con-001", "Reset password not working",
        "I clicked forgot password but never got the email. What now?", "high"),
    Ticket("tic-004", "acc-006", "con-006", "What are your API rate limits?",
        "We're building an integration and hitting 429s. What's the limit and how should we handle it?", "normal"),
    Ticket("tic-005", "acc-002", "con-003", "Need SSO with Okta",
        "We need SAML SSO via Okta for our org. Is it supported and how do we set it up?", "normal"),
    Ticket("tic-006", "acc-003", "con-004", "How long do you keep our data?",
        "Compliance is asking about your data retention period for event data.", "normal"),
    Ticket("tic-007", "acc-005", "con-001", "Change from annual to monthly billing",
        "We want to switch our annual plan to monthly. How does that work?", "low"),
    Ticket("tic-008", "acc-001", "con-002", "Set up a webhook for new events",
        "How do I receive a callback when certain events fire? Need payload details.", "normal"),
    Ticket("tic-009", "acc-006", "con-006", "Enable 2FA for everyone",
        "Can I require two-factor for all members, and what methods are supported?", "normal"),
    Ticket("tic-010", "acc-004", "con-005", "Connect our Snowflake warehouse",
        "How do we connect Snowflake and how often does it sync?", "normal"),
    # --- not cleanly answerable from KB → should escalate -------------------
    Ticket("tic-011", "acc-002", "con-003", "Dispute on last invoice — overcharged",
        "We were billed for 40 seats but only have 28 active. We want a refund for the difference.", "high"),
    Ticket("tic-012", "acc-004", "con-005", "We lost a dashboard and it's not in Trash",
        "A critical dashboard vanished and it's not in Trash. We need it restored urgently — this is affecting a board meeting.", "urgent"),
    Ticket("tic-013", "acc-002", "con-003", "Custom contract terms / DPA redlines",
        "Our legal team has redlines on your DPA and wants custom liability terms before renewal.", "high"),
    Ticket("tic-014", "acc-006", "con-006", "Feature request: anomaly alerts",
        "Do you have automated anomaly detection alerts? If not, can you add it? It's a deal-breaker for us.", "normal"),
    Ticket("tic-015", "acc-001", "con-001", "Bug: numbers don't match between two reports",
        "Two reports built on the same data show different totals. We think it's a bug in your aggregation.", "high"),
]

# --------------------------------------------------------------------------- #
# Inbound leads (qualifier flow). ICP ≈ mid/enterprise in saas/fintech/ecommerce
# with mid/high budget and real intent. score/status/routed_to written by agent.
# --------------------------------------------------------------------------- #
LEADS = [
    # clean fits → qualify + route
    Lead("lead-001", "Rita Cohen", "rita@brightcart.example", "BrightCart", "demo_request",
         "ecommerce", "mid", "high", "Requested demo; visited pricing 4x; 25-person data team."),
    Lead("lead-002", "Tomás Vidal", "tomas@ledgerly.example", "Ledgerly", "demo_request",
         "fintech", "enterprise", "high", "Booked a call; evaluating vs competitor; budget approved this quarter."),
    Lead("lead-003", "Aisha Bello", "aisha@stackpilot.example", "StackPilot", "content",
         "saas", "mid", "mid", "Downloaded benchmarking guide; asked about SSO and API limits."),
    # clear no's → disqualify
    Lead("lead-004", "Jordan Lee", "jordan@gmail.example", "(personal)", "webform",
         "", "smb", "none", "Student doing a class project; no budget; wants free access."),
    Lead("lead-005", "Pat Morgan", "pat@tinyshop.example", "TinyShop", "webform",
         "retail", "smb", "low", "One-person store; asked if there's a free forever plan."),
    # ambiguous → low-confidence handoff
    Lead("lead-006", "Wei Zhang", "wei@nimbus.example", "Nimbus Logistics", "demo_request",
         "logistics", "mid", "", "Requested demo but didn't share budget or use case; vague intent."),
    Lead("lead-007", "Sofia Maretti", "sofia@helixbio.example", "Helix Bio", "content",
         "healthcare", "enterprise", "mid", "Downloaded whitepaper; unclear if evaluating or researching; no timeline."),
]


def seed(db_path: str = "data/crm.db") -> SqliteStore:
    store = SqliteStore(db_path)
    store._wipe()
    for a in ACCOUNTS:
        store.insert_account(a)
    for c in CONTACTS:
        store.insert_contact(c)
    for d in DEALS:
        store.insert_deal(d)
    for act in ACTIVITIES:
        store.insert_activity(act)
    for k in KB:
        store.insert_kb_article(k)
    for t in TICKETS:
        store.insert_ticket(t)
    for lead in LEADS:
        store.insert_lead(lead)
    store.commit()
    return store


if __name__ == "__main__":
    s = seed()
    print(
        f"Seeded {len(ACCOUNTS)} accounts, {len(CONTACTS)} contacts, "
        f"{len(DEALS)} deals, {len(ACTIVITIES)} activities, {len(KB)} KB articles, "
        f"{len(TICKETS)} tickets, {len(LEADS)} leads → {s.db_path}"
    )
