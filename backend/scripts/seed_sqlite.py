"""
Seed SQLite DB — HackHERway PS6

Creates all tables and seeds:
  - 3 demo users (ARUN01, NEHA02, SARA03)
  - 8 designation templates (role access bundles)
  - dangerous_combinations (Privilege Guard data)
  - privilege_edges for NEHA02 (triggers Privilege Guard in Phase 4)
  - synthetic approval_events for Risk Scorer (ARUN01 scores ~78)
  - approver_routing (all → Teams webhook for demo)

Usage (from backend/ folder):
    python scripts/seed_sqlite.py
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ModuleNotFoundError:
    pass

DB_PATH = os.environ.get(
    "SQLITE_DB_PATH",
    str(Path(__file__).parent.parent / "hackherway.db"),
)

TEAMS_WEBHOOK = os.environ.get("TEAMS_WEBHOOK_URL", "")


def ts(year: int, month: int, day: int, hour: int = 10, minute: int = 0) -> int:
    """Return UTC Unix timestamp for the given date/time."""
    return int(datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp())


# ── Full Schema ───────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    acf2_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    team            TEXT,
    manager         TEXT,
    dept            TEXT,
    employment_type TEXT
);

CREATE TABLE IF NOT EXISTS designations (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    team_hint       TEXT,
    dept_hint       TEXT,
    mandatory_items TEXT NOT NULL,
    optional_items  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_requests (
    id               TEXT PRIMARY KEY,
    acf2_id          TEXT NOT NULL,
    designation_id   TEXT,
    final_bundle     TEXT,
    risk_score       INTEGER,
    risk_explanation TEXT,
    status           TEXT DEFAULT 'pending',
    servicenow_ritm  TEXT,
    created_at       INTEGER NOT NULL,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id)
);

CREATE TABLE IF NOT EXISTS approval_events (
    id                TEXT PRIMARY KEY,
    access_request_id TEXT,
    acf2_id           TEXT NOT NULL,
    role              TEXT,
    team              TEXT,
    access_item       TEXT NOT NULL,
    approver          TEXT,
    status            TEXT DEFAULT 'pending',
    submitted_at      INTEGER NOT NULL,
    resolved_at       INTEGER,
    off_hours         INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS approver_routing (
    id                TEXT PRIMARY KEY,
    access_item       TEXT NOT NULL,
    approver_name     TEXT,
    approver_email    TEXT,
    teams_webhook_url TEXT,
    team              TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id                TEXT PRIMARY KEY,
    acf2_id           TEXT,
    access_request_id TEXT,
    event_type        TEXT NOT NULL,
    details           TEXT,
    created_at        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS privilege_edges (
    id          TEXT PRIMARY KEY,
    acf2_id     TEXT NOT NULL,
    access_item TEXT NOT NULL,
    granted_at  INTEGER NOT NULL,
    granted_by  TEXT,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id)
);

CREATE TABLE IF NOT EXISTS dangerous_combinations (
    id            TEXT PRIMARY KEY,
    access_item_a TEXT NOT NULL,
    access_item_b TEXT NOT NULL,
    severity      TEXT NOT NULL,
    reason        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS template_drafts (
    id             TEXT PRIMARY KEY,
    acf2_id        TEXT NOT NULL,
    proposed_name  TEXT,
    proposed_items TEXT,
    status         TEXT DEFAULT 'pending_ratification',
    created_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    acf2_id    TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'bot')),
    content         TEXT NOT NULL,
    created_at      INTEGER NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);
"""

# ── Demo Users ────────────────────────────────────────────────────────────────

USERS = [
    ("ARUN01", "Arun Mehta",  "Cloud Infrastructure", "Raj Kumar",   "Technology", "full-time"),
    ("NEHA02", "Neha Kapoor", "Finance Analytics",    "Deepa Menon", "Finance",    "contract"),
    ("SARA03", "Sara Chen",   "TBD",                  "TBD",         "TBD",        "full-time"),
]

RETIRED_IDS = ("RIYA001", "JOHN002", "PRIYA003", "SAM004")

# ── Designation Templates (8) ─────────────────────────────────────────────────
# Context stuffing: all 8 templates loaded into agent system prompt.
# Agent does fuzzy matching — SQL not used for template retrieval.

DESIGNATIONS = [
    {
        "id": "backend_developer",
        "name": "Backend Developer",
        "description": "Software engineer building server-side services and APIs",
        "team_hint": "backend, payments, engineering, services, api",
        "dept_hint": "technology",
        "mandatory_items": json.dumps([
            "github_repo_access",
            "jira_project_access",
            "npe_db_read",
            "npe_environment",
        ]),
        "optional_items": json.dumps([
            "prod_db_read",
            "cyberark_pam",
            "github_copilot",
            "aws_dev_console",
        ]),
    },
    {
        "id": "devops_cloud_engineer",
        "name": "DevOps / Cloud Engineer",
        "description": "Engineer managing cloud infrastructure, CI/CD pipelines, and platform operations",
        "team_hint": "cloud infrastructure, devops, platform, site reliability, sre",
        "dept_hint": "technology",
        "mandatory_items": json.dumps([
            "github_repo_access",
            "jira_project_access",
            "aws_restricted_console",
            "terraform_state_access",
        ]),
        "optional_items": json.dumps([
            "aws_prod_admin",
            "pagerduty",
            "cyberark_pam",
            "deploy_pipeline_write",
        ]),
    },
    {
        "id": "data_analyst",
        "name": "Data Analyst",
        "description": "Analyst working with data pipelines, reporting, and business intelligence",
        "team_hint": "analytics, data, reporting, business intelligence, bi",
        "dept_hint": "technology, finance, operations",
        "mandatory_items": json.dumps([
            "data_warehouse_read",
            "jira_project_access",
            "reporting_tools",
        ]),
        "optional_items": json.dumps([
            "prod_db_read",
            "extended_schema_access",
            "python_notebook_access",
        ]),
    },
    {
        "id": "finance_analyst",
        "name": "Finance Analyst",
        "description": "Analyst working with financial data, reporting, and compliance systems",
        "team_hint": "finance analytics, finance, actuarial, risk, investment",
        "dept_hint": "finance",
        "mandatory_items": json.dumps([
            "finance_systems_read",
            "jira_project_access",
            "sap_view",
            "finance_data_read",
        ]),
        "optional_items": json.dumps([
            "finance_systems_write",
            "external_reporting_api",
        ]),
    },
    {
        "id": "intern",
        "name": "Intern",
        "description": "Intern with restricted access to non-production environments only",
        "team_hint": "any",
        "dept_hint": "any",
        "mandatory_items": json.dumps([
            "jira_project_access",
            "internal_wiki",
            "npe_environment",
        ]),
        "optional_items": json.dumps([
            "github_repo_access_readonly",
            "npe_db_read",
        ]),
    },
    {
        "id": "manager_team_lead",
        "name": "Manager / Team Lead",
        "description": "People manager or technical lead with team oversight access",
        "team_hint": "any",
        "dept_hint": "any",
        "mandatory_items": json.dumps([
            "github_repo_access",
            "jira_admin",
            "team_management_dashboard",
            "org_chart_access",
        ]),
        "optional_items": json.dumps([
            "admin_console_read",
            "budget_reporting",
            "hr_system_read",
        ]),
    },
    {
        "id": "auditor",
        "name": "Auditor",
        "description": "Internal or external auditor with read-only access to compliance data",
        "team_hint": "compliance, audit, risk, internal audit, regulatory",
        "dept_hint": "any",
        "mandatory_items": json.dumps([
            "audit_log_read",
            "compliance_reporting",
            "jira_project_access_readonly",
        ]),
        "optional_items": json.dumps([
            "extended_audit_scope",
            "finance_data_read",
        ]),
    },
    {
        "id": "contractor",
        "name": "Contractor",
        "description": "External contractor with limited, scoped access per project",
        "team_hint": "any",
        "dept_hint": "any",
        "mandatory_items": json.dumps([
            "jira_project_access",
            "nda_systems",
            "contractor_vpn",
        ]),
        "optional_items": json.dumps([
            "github_repo_access_readonly",
            "npe_environment",
            "reporting_tools",
        ]),
    },
]

# ── Dangerous Combinations ────────────────────────────────────────────────────
# Privilege Guard (Phase 4) checks user's privilege_edges + requested items
# against this table. Severity: HIGH = warn + confirm, CRITICAL = warn + auto-escalate.

DANGEROUS_COMBINATIONS = [
    {
        "id": "danger_001",
        "access_item_a": "prod_db_write",
        "access_item_b": "deploy_pipeline_write",
        "severity": "CRITICAL",
        "reason": (
            "Write access to the production database combined with deploy pipeline "
            "write access enables unauthorized code deployment with simultaneous "
            "data manipulation — full production system compromise."
        ),
    },
    {
        "id": "danger_002",
        "access_item_a": "prod_db_read",
        "access_item_b": "deploy_pipeline_write",
        "severity": "HIGH",
        "reason": (
            "Read access to production data combined with deploy pipeline write "
            "creates a data exfiltration vector — production data can be extracted "
            "and pushed via a malicious deployment."
        ),
    },
    {
        "id": "danger_003",
        "access_item_a": "finance_data_read",
        "access_item_b": "external_reporting_api",
        "severity": "HIGH",
        "reason": (
            "Finance data read access combined with external reporting API write "
            "creates a finance data exfiltration vector to external systems. "
            "Requires explicit CISO approval."
        ),
    },
    {
        "id": "danger_004",
        "access_item_a": "finance_systems_write",
        "access_item_b": "external_reporting_api",
        "severity": "CRITICAL",
        "reason": (
            "Write access to finance systems combined with external reporting API "
            "enables unauthorized modification of financial records and exfiltration "
            "to external systems — regulatory and financial integrity risk."
        ),
    },
    {
        "id": "danger_005",
        "access_item_a": "npe_environment",
        "access_item_b": "prod_db_write",
        "severity": "HIGH",
        "reason": (
            "NPE environment access combined with production database write "
            "violates the non-production / production access boundary and "
            "increases risk of accidental or malicious production data modification."
        ),
    },
]

# ── Privilege Edges for NEHA02 ────────────────────────────────────────────────
# NEHA02 already has finance_data_read + prod_db_read from a previous role.
#
# Demo trigger path (Phase 4):
#   NEHA02 requests Finance Analyst template.
#   Mandatory items include finance_data_read (she already has it — overlap OK).
#   Optional items include external_reporting_api.
#   Privilege Guard: finance_data_read (existing) + external_reporting_api (requested)
#   → matches danger_003 → severity HIGH → warning fires before submission.

PRIVILEGE_EDGES = [
    {
        "id": str(uuid.uuid4()),
        "acf2_id": "NEHA02",
        "access_item": "finance_data_read",
        "granted_at": ts(2025, 1, 15),
        "granted_by": "Deepa Menon",
    },
    {
        "id": str(uuid.uuid4()),
        "acf2_id": "NEHA02",
        "access_item": "prod_db_read",
        "granted_at": ts(2025, 3, 1),
        "granted_by": "Deepa Menon",
    },
]

# ── Approver Routing ──────────────────────────────────────────────────────────
# All items route to a single Teams webhook for demo.
# TEAMS_WEBHOOK_URL is read from .env (empty in .env.example — fill in Phase 5).

_ALL_ACCESS_ITEMS = [
    "github_repo_access", "jira_project_access", "npe_db_read", "npe_environment",
    "prod_db_read", "prod_db_write", "cyberark_pam", "github_copilot",
    "aws_dev_console", "aws_restricted_console", "terraform_state_access",
    "aws_prod_admin", "pagerduty", "deploy_pipeline_write",
    "data_warehouse_read", "reporting_tools", "extended_schema_access",
    "python_notebook_access", "finance_systems_read", "finance_systems_write",
    "sap_view", "finance_data_read", "external_reporting_api",
    "internal_wiki", "github_repo_access_readonly", "jira_admin",
    "team_management_dashboard", "org_chart_access", "admin_console_read",
    "budget_reporting", "hr_system_read", "audit_log_read",
    "compliance_reporting", "jira_project_access_readonly", "extended_audit_scope",
    "nda_systems", "contractor_vpn",
]

APPROVER_ROUTING = [
    {
        "id": str(uuid.uuid4()),
        "access_item": item,
        "approver_name": "Demo Approver",
        "approver_email": "approver@sunlife.com",
        "teams_webhook_url": TEAMS_WEBHOOK,
        "team": "all",
    }
    for item in _ALL_ACCESS_ITEMS
]

# ── Historical Approval Events for Risk Scorer ────────────────────────────────
# Risk Scorer (Phase 4) queries approval_events for role baseline and ARUN01
# anomalies, then computes a 0-100 score.
#
# Baseline: 10 normal DevOps events from other historical users — all approved,
#           all business hours, all standard items.
#
# ARUN01 anomalies that drive score to ~78:
#   1. prod_db_write at 2:17 AM          → REJECTED (off-hours + wrong item for role)
#   2. deploy_pipeline_write at 2:19 AM  → REJECTED (velocity: 2 min gap + off-hours)
#   3. prod_db_write again 3 days later  → REJECTED (high re-request velocity)
#   4. aws_prod_admin with escalation    → APPROVED (manager override)
#   5. cyberark_pam normal request       → APPROVED

def _event(acf2_id, role, team, item, approver, status, submitted_at, resolved_at, off_hours=0):
    return {
        "id": str(uuid.uuid4()),
        "access_request_id": None,
        "acf2_id": acf2_id,
        "role": role,
        "team": team,
        "access_item": item,
        "approver": approver,
        "status": status,
        "submitted_at": submitted_at,
        "resolved_at": resolved_at,
        "off_hours": off_hours,
    }

APPROVAL_EVENTS = [
    # ── Baseline: normal Cloud Infra / DevOps events from historical users ──
    _event("HIST001", "devops_cloud_engineer", "Cloud Infrastructure",
           "github_repo_access", "Raj Kumar", "approved",
           ts(2025, 1, 5, 11), ts(2025, 1, 5, 14)),
    _event("HIST002", "devops_cloud_engineer", "Cloud Infrastructure",
           "aws_restricted_console", "Raj Kumar", "approved",
           ts(2025, 1, 8, 14), ts(2025, 1, 8, 16)),
    _event("HIST003", "devops_cloud_engineer", "Cloud Infrastructure",
           "terraform_state_access", "Raj Kumar", "approved",
           ts(2025, 1, 10, 9), ts(2025, 1, 10, 11)),
    _event("HIST004", "devops_cloud_engineer", "Cloud Infrastructure",
           "jira_project_access", "Raj Kumar", "approved",
           ts(2025, 1, 14, 13), ts(2025, 1, 14, 15)),
    _event("HIST005", "devops_cloud_engineer", "Cloud Infrastructure",
           "pagerduty", "Raj Kumar", "approved",
           ts(2025, 1, 17, 10), ts(2025, 1, 17, 12)),
    _event("HIST006", "devops_cloud_engineer", "Cloud Infrastructure",
           "github_repo_access", "Raj Kumar", "approved",
           ts(2025, 1, 20, 15), ts(2025, 1, 20, 17)),
    _event("HIST001", "devops_cloud_engineer", "Cloud Infrastructure",
           "cyberark_pam", "Raj Kumar", "approved",
           ts(2025, 1, 22, 11), ts(2025, 1, 22, 14)),
    _event("HIST002", "devops_cloud_engineer", "Cloud Infrastructure",
           "jira_project_access", "Raj Kumar", "approved",
           ts(2025, 1, 24, 14), ts(2025, 1, 24, 16)),
    _event("HIST003", "devops_cloud_engineer", "Cloud Infrastructure",
           "terraform_state_access", "Raj Kumar", "approved",
           ts(2025, 1, 27, 9), ts(2025, 1, 27, 11)),
    _event("HIST004", "devops_cloud_engineer", "Cloud Infrastructure",
           "aws_restricted_console", "Raj Kumar", "approved",
           ts(2025, 1, 29, 16), ts(2025, 1, 29, 17)),

    # ── ARUN01 anomalous events ──
    # Event 1: prod_db_write at 2:17 AM — unusual item + off-hours → REJECTED
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure",
           "prod_db_write", "Raj Kumar", "rejected",
           ts(2025, 2, 3, 2, 17), ts(2025, 2, 3, 9, 0), off_hours=1),

    # Event 2: deploy_pipeline_write 2 min later — velocity spike + off-hours → REJECTED
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure",
           "deploy_pipeline_write", "Raj Kumar", "rejected",
           ts(2025, 2, 3, 2, 19), ts(2025, 2, 3, 9, 5), off_hours=1),

    # Event 3: prod_db_write re-request 3 days later — high velocity re-request → REJECTED
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure",
           "prod_db_write", "Raj Kumar", "rejected",
           ts(2025, 2, 6, 14, 5), ts(2025, 2, 6, 17, 0)),

    # Event 4: aws_prod_admin — escalation pattern, approved via manager's manager
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure",
           "aws_prod_admin", "Vikram Nair", "approved",
           ts(2025, 2, 10, 16, 30), ts(2025, 2, 11, 10, 0)),

    # Event 5: cyberark_pam — normal request, approved
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure",
           "cyberark_pam", "Raj Kumar", "approved",
           ts(2025, 2, 15, 10, 0), ts(2025, 2, 15, 14, 0)),
]


# ── Main seed ─────────────────────────────────────────────────────────────────

def seed():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)

    # Remove retired demo users from old architecture
    db.executemany(
        "DELETE FROM users WHERE acf2_id = ?",
        [(i,) for i in RETIRED_IDS],
    )

    # Users
    print("Users:")
    for (acf2_id, name, team, manager, dept, emp_type) in USERS:
        db.execute(
            """INSERT INTO users (acf2_id, name, team, manager, dept, employment_type)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(acf2_id) DO UPDATE SET
                 name=excluded.name, team=excluded.team,
                 manager=excluded.manager, dept=excluded.dept,
                 employment_type=excluded.employment_type""",
            (acf2_id, name, team, manager, dept, emp_type),
        )
        print(f"  seeded: {acf2_id} - {name}")

    # Designation templates
    print("\nDesignation templates:")
    for d in DESIGNATIONS:
        db.execute(
            """INSERT INTO designations
               (id, name, description, team_hint, dept_hint, mandatory_items, optional_items)
               VALUES (:id, :name, :description, :team_hint, :dept_hint, :mandatory_items, :optional_items)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, description=excluded.description,
                 team_hint=excluded.team_hint, dept_hint=excluded.dept_hint,
                 mandatory_items=excluded.mandatory_items,
                 optional_items=excluded.optional_items""",
            d,
        )
        print(f"  template: {d['id']}")

    # Dangerous combinations
    print("\nDangerous combinations:")
    db.execute("DELETE FROM dangerous_combinations")
    for combo in DANGEROUS_COMBINATIONS:
        db.execute(
            """INSERT INTO dangerous_combinations
               (id, access_item_a, access_item_b, severity, reason)
               VALUES (:id, :access_item_a, :access_item_b, :severity, :reason)""",
            combo,
        )
        print(f"  [{combo['severity']}] {combo['access_item_a']} + {combo['access_item_b']}")

    # Privilege edges for NEHA02
    print("\nPrivilege edges (NEHA02):")
    db.execute("DELETE FROM privilege_edges WHERE acf2_id = 'NEHA02'")
    for edge in PRIVILEGE_EDGES:
        db.execute(
            """INSERT INTO privilege_edges (id, acf2_id, access_item, granted_at, granted_by)
               VALUES (:id, :acf2_id, :access_item, :granted_at, :granted_by)""",
            edge,
        )
        print(f"  edge: NEHA02 -> {edge['access_item']}")

    # Approver routing
    db.execute("DELETE FROM approver_routing")
    for route in APPROVER_ROUTING:
        db.execute(
            """INSERT INTO approver_routing
               (id, access_item, approver_name, approver_email, teams_webhook_url, team)
               VALUES (:id, :access_item, :approver_name, :approver_email, :teams_webhook_url, :team)""",
            route,
        )
    print(f"\nApprover routing: {len(APPROVER_ROUTING)} access items -> Teams webhook")

    # Historical approval events
    historical_acf2 = ("HIST001", "HIST002", "HIST003", "HIST004", "HIST005",
                       "HIST006", "ARUN01")
    db.executemany(
        "DELETE FROM approval_events WHERE acf2_id = ?",
        [(i,) for i in historical_acf2],
    )
    for event in APPROVAL_EVENTS:
        db.execute(
            """INSERT INTO approval_events
               (id, access_request_id, acf2_id, role, team, access_item,
                approver, status, submitted_at, resolved_at, off_hours)
               VALUES (:id, :access_request_id, :acf2_id, :role, :team, :access_item,
                       :approver, :status, :submitted_at, :resolved_at, :off_hours)""",
            event,
        )
    arun_anomalies = sum(1 for e in APPROVAL_EVENTS if e["acf2_id"] == "ARUN01")
    baseline_count = len(APPROVAL_EVENTS) - arun_anomalies
    print(f"\nApproval events:")
    print(f"  baseline (normal): {baseline_count} events (HIST001-006, devops role)")
    print(f"  ARUN01 anomalies:  {arun_anomalies} events (2 off-hours, 3 rejections -> score ~78)")

    db.commit()
    db.close()
    print(f"\nDone. DB at: {DB_PATH}")


if __name__ == "__main__":
    seed()
