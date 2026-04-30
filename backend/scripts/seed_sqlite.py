"""
Seed SQLite DB - HackHERway PS6.

Phase 0B normalized schema:
  - 3 demo users: ARUN01, NEHA02, SARA03
  - 8 role designations
  - role_access_items rows for every mandatory and optional access item
  - user_designations for ARUN01 and NEHA02 only
  - dangerous_combinations, privilege_edges, approval_events, approver_routing

Usage, from backend/:
    python scripts/seed_sqlite.py
"""

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


SCHEMA = """
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS template_drafts;
DROP TABLE IF EXISTS dangerous_combinations;
DROP TABLE IF EXISTS privilege_edges;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS approver_routing;
DROP TABLE IF EXISTS approval_events;
DROP TABLE IF EXISTS access_requests;
DROP TABLE IF EXISTS ritm_requests;
DROP TABLE IF EXISTS role_access_items;
DROP TABLE IF EXISTS user_designations;
DROP TABLE IF EXISTS designations;
DROP TABLE IF EXISTS users;

PRAGMA foreign_keys = ON;

CREATE TABLE users (
    acf2_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    team            TEXT,
    manager         TEXT,
    dept            TEXT,
    employment_type TEXT
);

CREATE TABLE designations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    team_hint   TEXT,
    dept_hint   TEXT
);

CREATE TABLE user_designations (
    acf2_id        TEXT PRIMARY KEY,
    designation_id TEXT NOT NULL,
    assigned_at    INTEGER NOT NULL,
    source         TEXT NOT NULL,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id),
    FOREIGN KEY(designation_id) REFERENCES designations(id)
);

CREATE TABLE role_access_items (
    id                         TEXT PRIMARY KEY,
    designation_id             TEXT NOT NULL,
    access_item                TEXT NOT NULL,
    display_name               TEXT,
    system                     TEXT,
    description                TEXT,
    mandatory                  INTEGER NOT NULL CHECK(mandatory IN (0, 1)),
    owner_team                 TEXT,
    servicenow_catalog_item_id TEXT,
    sort_order                 INTEGER,
    FOREIGN KEY(designation_id) REFERENCES designations(id)
);

CREATE TABLE access_requests (
    id               TEXT PRIMARY KEY,
    acf2_id          TEXT NOT NULL,
    designation_id   TEXT,
    final_bundle     TEXT,
    risk_score       INTEGER,
    risk_explanation TEXT,
    status           TEXT DEFAULT 'pending',
    servicenow_ritm  TEXT,
    created_at       INTEGER NOT NULL,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id),
    FOREIGN KEY(designation_id) REFERENCES designations(id)
);

CREATE TABLE approval_events (
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
    off_hours         INTEGER DEFAULT 0,
    FOREIGN KEY(access_request_id) REFERENCES access_requests(id)
);

CREATE TABLE approver_routing (
    id                TEXT PRIMARY KEY,
    access_item       TEXT NOT NULL,
    approver_name     TEXT,
    approver_email    TEXT,
    teams_webhook_url TEXT,
    team              TEXT
);

CREATE TABLE audit_log (
    id                TEXT PRIMARY KEY,
    acf2_id           TEXT,
    access_request_id TEXT,
    event_type        TEXT NOT NULL,
    details           TEXT,
    created_at        INTEGER NOT NULL
);

CREATE TABLE privilege_edges (
    id          TEXT PRIMARY KEY,
    acf2_id     TEXT NOT NULL,
    access_item TEXT NOT NULL,
    granted_at  INTEGER NOT NULL,
    granted_by  TEXT,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id)
);

CREATE TABLE dangerous_combinations (
    id            TEXT PRIMARY KEY,
    access_item_a TEXT NOT NULL,
    access_item_b TEXT NOT NULL,
    severity      TEXT NOT NULL,
    reason        TEXT NOT NULL
);

CREATE TABLE template_drafts (
    id             TEXT PRIMARY KEY,
    acf2_id        TEXT NOT NULL,
    proposed_name  TEXT,
    proposed_items TEXT,
    status         TEXT DEFAULT 'pending_ratification',
    created_at     INTEGER NOT NULL,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id)
);

CREATE TABLE conversations (
    id         TEXT PRIMARY KEY,
    acf2_id    TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY(acf2_id) REFERENCES users(acf2_id)
);

CREATE TABLE messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'bot')),
    content         TEXT NOT NULL,
    created_at      INTEGER NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);
"""


USERS = [
    ("ARUN01", "Arun Mehta", "Cloud Infrastructure", "Raj Kumar", "Technology", "full-time"),
    ("NEHA02", "Neha Kapoor", "Finance Analytics", "Deepa Menon", "Finance", "contract"),
    ("SARA03", "Sara Chen", "TBD", "TBD", "TBD", "full-time"),
]

DESIGNATIONS = [
    {
        "id": "backend_developer",
        "title": "Backend Developer",
        "description": "Software engineer building server-side services and APIs",
        "team_hint": "backend, payments, engineering, services, api",
        "dept_hint": "technology",
    },
    {
        "id": "devops_cloud_engineer",
        "title": "DevOps / Cloud Engineer",
        "description": "Engineer managing cloud infrastructure, CI/CD pipelines, and platform operations",
        "team_hint": "cloud infrastructure, devops, platform, site reliability, sre",
        "dept_hint": "technology",
    },
    {
        "id": "data_analyst",
        "title": "Data Analyst",
        "description": "Analyst working with data pipelines, reporting, and business intelligence",
        "team_hint": "analytics, data, reporting, business intelligence, bi",
        "dept_hint": "technology, finance, operations",
    },
    {
        "id": "finance_analyst",
        "title": "Finance Analyst",
        "description": "Analyst working with financial data, reporting, and compliance systems",
        "team_hint": "finance analytics, finance, actuarial, risk, investment",
        "dept_hint": "finance",
    },
    {
        "id": "intern",
        "title": "Intern",
        "description": "Intern with restricted access to non-production environments only",
        "team_hint": "any",
        "dept_hint": "any",
    },
    {
        "id": "manager_team_lead",
        "title": "Manager / Team Lead",
        "description": "People manager or technical lead with team oversight access",
        "team_hint": "any",
        "dept_hint": "any",
    },
    {
        "id": "auditor",
        "title": "Auditor",
        "description": "Internal or external auditor with read-only access to compliance data",
        "team_hint": "compliance, audit, risk, internal audit, regulatory",
        "dept_hint": "any",
    },
    {
        "id": "contractor",
        "title": "Contractor",
        "description": "External contractor with limited, scoped access per project",
        "team_hint": "any",
        "dept_hint": "any",
    },
]

DESIGNATION_ACCESS = {
    "backend_developer": {
        "mandatory": [
            "github_repo_access",
            "jira_project_access",
            "npe_db_read",
            "npe_environment",
        ],
        "optional": [
            "prod_db_read",
            "cyberark_pam",
            "github_copilot",
            "aws_dev_console",
        ],
    },
    "devops_cloud_engineer": {
        "mandatory": [
            "github_repo_access",
            "jira_project_access",
            "aws_restricted_console",
            "terraform_state_access",
        ],
        "optional": [
            "aws_prod_admin",
            "pagerduty",
            "cyberark_pam",
            "deploy_pipeline_write",
        ],
    },
    "data_analyst": {
        "mandatory": [
            "data_warehouse_read",
            "jira_project_access",
            "reporting_tools",
        ],
        "optional": [
            "prod_db_read",
            "extended_schema_access",
            "python_notebook_access",
        ],
    },
    "finance_analyst": {
        "mandatory": [
            "finance_systems_read",
            "jira_project_access",
            "sap_view",
            "finance_data_read",
        ],
        "optional": [
            "finance_systems_write",
            "external_reporting_api",
        ],
    },
    "intern": {
        "mandatory": [
            "jira_project_access",
            "internal_wiki",
            "npe_environment",
        ],
        "optional": [
            "github_repo_access_readonly",
            "npe_db_read",
        ],
    },
    "manager_team_lead": {
        "mandatory": [
            "github_repo_access",
            "jira_admin",
            "team_management_dashboard",
            "org_chart_access",
        ],
        "optional": [
            "admin_console_read",
            "budget_reporting",
            "hr_system_read",
        ],
    },
    "auditor": {
        "mandatory": [
            "audit_log_read",
            "compliance_reporting",
            "jira_project_access_readonly",
        ],
        "optional": [
            "extended_audit_scope",
            "finance_data_read",
        ],
    },
    "contractor": {
        "mandatory": [
            "jira_project_access",
            "nda_systems",
            "contractor_vpn",
        ],
        "optional": [
            "github_repo_access_readonly",
            "npe_environment",
            "reporting_tools",
        ],
    },
}

ACCESS_CATALOG = {
    "github_repo_access": ("GitHub repository access", "GitHub", "Required for source code work", "Engineering Tools"),
    "jira_project_access": ("Jira project access", "Jira", "Required for delivery tracking and assigned work", "Agile Tools"),
    "npe_db_read": ("Non-production database read", "Database", "Read access for development and test data", "Database Operations"),
    "npe_environment": ("Non-production environment", "Cloud", "Access to development and test environments", "Cloud Platform"),
    "prod_db_read": ("Production database read", "Database", "Read-only access to production data where approved", "Database Operations"),
    "prod_db_write": ("Production database write", "Database", "Write access to production data", "Database Operations"),
    "cyberark_pam": ("CyberArk PAM", "CyberArk", "Privileged session checkout for approved systems", "Identity Security"),
    "github_copilot": ("GitHub Copilot", "GitHub", "Optional coding assistant for engineering work", "Engineering Tools"),
    "aws_dev_console": ("AWS development console", "AWS", "Console access to development AWS accounts", "Cloud Platform"),
    "aws_restricted_console": ("AWS restricted console", "AWS", "Restricted console access for platform operations", "Cloud Platform"),
    "terraform_state_access": ("Terraform state access", "Terraform", "Access to infrastructure state files", "Cloud Platform"),
    "aws_prod_admin": ("AWS production admin", "AWS", "Elevated production cloud administration", "Cloud Platform"),
    "pagerduty": ("PagerDuty", "PagerDuty", "On-call alerting and incident response access", "Service Reliability"),
    "deploy_pipeline_write": ("Deploy pipeline write", "CI/CD", "Permission to update deployment pipelines", "DevOps Platform"),
    "data_warehouse_read": ("Data warehouse read", "Data Warehouse", "Read access to analytics warehouse datasets", "Data Platform"),
    "reporting_tools": ("Reporting tools", "BI", "Access to reporting and dashboard tools", "Business Intelligence"),
    "extended_schema_access": ("Extended schema access", "Data Warehouse", "Expanded analytics schema visibility", "Data Platform"),
    "python_notebook_access": ("Python notebook access", "Notebook", "Notebook workspace access for analysis", "Data Platform"),
    "finance_systems_read": ("Finance systems read", "Finance Systems", "Read-only access to financial systems", "Finance Technology"),
    "finance_systems_write": ("Finance systems write", "Finance Systems", "Write access to financial systems", "Finance Technology"),
    "sap_view": ("SAP view", "SAP", "Read access for SAP financial records", "Finance Technology"),
    "finance_data_read": ("Finance data read", "Finance Data", "Read access to controlled finance datasets", "Finance Data Governance"),
    "external_reporting_api": ("External reporting API", "Reporting API", "API access for external reporting integrations", "Finance Technology"),
    "internal_wiki": ("Internal wiki", "Confluence", "Access to internal documentation", "Knowledge Management"),
    "github_repo_access_readonly": ("GitHub repository read-only", "GitHub", "Read-only source repository access", "Engineering Tools"),
    "jira_admin": ("Jira admin", "Jira", "Administrative access for Jira projects", "Agile Tools"),
    "team_management_dashboard": ("Team management dashboard", "Management Portal", "Team delivery and staffing dashboard access", "People Systems"),
    "org_chart_access": ("Organization chart access", "Workday", "Organization structure lookup access", "People Systems"),
    "admin_console_read": ("Admin console read", "Admin Portal", "Read-only administrative console visibility", "Platform Operations"),
    "budget_reporting": ("Budget reporting", "Finance Reporting", "Budget dashboard and forecast visibility", "Finance Technology"),
    "hr_system_read": ("HR system read", "Workday", "Read-only HR context for team management", "People Systems"),
    "audit_log_read": ("Audit log read", "Audit Platform", "Read-only access to audit evidence", "Compliance Technology"),
    "compliance_reporting": ("Compliance reporting", "Compliance Platform", "Access to compliance reports", "Compliance Technology"),
    "jira_project_access_readonly": ("Jira project read-only", "Jira", "Read-only project tracking access", "Agile Tools"),
    "extended_audit_scope": ("Extended audit scope", "Audit Platform", "Expanded read-only audit evidence access", "Compliance Technology"),
    "nda_systems": ("NDA systems", "Legal Portal", "Access to contractor agreement systems", "Legal Operations"),
    "contractor_vpn": ("Contractor VPN", "VPN", "Network access scoped for external contractors", "Network Operations"),
}


def catalog_id(access_item: str) -> str:
    return "SN-" + access_item.upper().replace("_", "-")


def role_access_rows():
    for designation_id, groups in DESIGNATION_ACCESS.items():
        order = 10
        for mandatory, items in ((1, groups["mandatory"]), (0, groups["optional"])):
            for access_item in items:
                display_name, system, description, owner_team = ACCESS_CATALOG[access_item]
                yield {
                    "id": f"{designation_id}:{access_item}",
                    "designation_id": designation_id,
                    "access_item": access_item,
                    "display_name": display_name,
                    "system": system,
                    "description": description,
                    "mandatory": mandatory,
                    "owner_team": owner_team,
                    "servicenow_catalog_item_id": catalog_id(access_item),
                    "sort_order": order,
                }
                order += 10


USER_DESIGNATIONS = [
    {
        "acf2_id": "ARUN01",
        "designation_id": "devops_cloud_engineer",
        "assigned_at": ts(2026, 4, 30),
        "source": "seed",
    },
    {
        "acf2_id": "NEHA02",
        "designation_id": "finance_analyst",
        "assigned_at": ts(2026, 4, 30),
        "source": "seed",
    },
]

DANGEROUS_COMBINATIONS = [
    {
        "id": "danger_001",
        "access_item_a": "prod_db_write",
        "access_item_b": "deploy_pipeline_write",
        "severity": "CRITICAL",
        "reason": "Production database write plus deploy pipeline write can enable unauthorized production changes.",
    },
    {
        "id": "danger_002",
        "access_item_a": "prod_db_read",
        "access_item_b": "deploy_pipeline_write",
        "severity": "HIGH",
        "reason": "Production data read plus deploy pipeline write creates a data exfiltration path.",
    },
    {
        "id": "danger_003",
        "access_item_a": "finance_data_read",
        "access_item_b": "external_reporting_api",
        "severity": "HIGH",
        "reason": "Finance data read plus external reporting API can expose controlled financial data.",
    },
    {
        "id": "danger_004",
        "access_item_a": "finance_systems_write",
        "access_item_b": "external_reporting_api",
        "severity": "CRITICAL",
        "reason": "Finance write access plus external reporting can affect financial integrity and reporting.",
    },
    {
        "id": "danger_005",
        "access_item_a": "npe_environment",
        "access_item_b": "prod_db_write",
        "severity": "HIGH",
        "reason": "Non-production access plus production database write violates environment separation.",
    },
]

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

APPROVER_ROUTING = [
    {
        "id": str(uuid.uuid4()),
        "access_item": item,
        "approver_name": "Demo Approver",
        "approver_email": "approver@sunlife.com",
        "teams_webhook_url": TEAMS_WEBHOOK,
        "team": "all",
    }
    for item in ACCESS_CATALOG.keys()
]


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
    _event("HIST001", "devops_cloud_engineer", "Cloud Infrastructure", "github_repo_access", "Raj Kumar", "approved", ts(2025, 1, 5, 11), ts(2025, 1, 5, 14)),
    _event("HIST002", "devops_cloud_engineer", "Cloud Infrastructure", "aws_restricted_console", "Raj Kumar", "approved", ts(2025, 1, 8, 14), ts(2025, 1, 8, 16)),
    _event("HIST003", "devops_cloud_engineer", "Cloud Infrastructure", "terraform_state_access", "Raj Kumar", "approved", ts(2025, 1, 10, 9), ts(2025, 1, 10, 11)),
    _event("HIST004", "devops_cloud_engineer", "Cloud Infrastructure", "jira_project_access", "Raj Kumar", "approved", ts(2025, 1, 14, 13), ts(2025, 1, 14, 15)),
    _event("HIST005", "devops_cloud_engineer", "Cloud Infrastructure", "pagerduty", "Raj Kumar", "approved", ts(2025, 1, 17, 10), ts(2025, 1, 17, 12)),
    _event("HIST006", "devops_cloud_engineer", "Cloud Infrastructure", "github_repo_access", "Raj Kumar", "approved", ts(2025, 1, 20, 15), ts(2025, 1, 20, 17)),
    _event("HIST001", "devops_cloud_engineer", "Cloud Infrastructure", "cyberark_pam", "Raj Kumar", "approved", ts(2025, 1, 22, 11), ts(2025, 1, 22, 14)),
    _event("HIST002", "devops_cloud_engineer", "Cloud Infrastructure", "jira_project_access", "Raj Kumar", "approved", ts(2025, 1, 24, 14), ts(2025, 1, 24, 16)),
    _event("HIST003", "devops_cloud_engineer", "Cloud Infrastructure", "terraform_state_access", "Raj Kumar", "approved", ts(2025, 1, 27, 9), ts(2025, 1, 27, 11)),
    _event("HIST004", "devops_cloud_engineer", "Cloud Infrastructure", "aws_restricted_console", "Raj Kumar", "approved", ts(2025, 1, 29, 16), ts(2025, 1, 29, 17)),
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure", "prod_db_write", "Raj Kumar", "rejected", ts(2025, 2, 3, 2, 17), ts(2025, 2, 3, 9, 0), off_hours=1),
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure", "deploy_pipeline_write", "Raj Kumar", "rejected", ts(2025, 2, 3, 2, 19), ts(2025, 2, 3, 9, 5), off_hours=1),
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure", "prod_db_write", "Raj Kumar", "rejected", ts(2025, 2, 6, 14, 5), ts(2025, 2, 6, 17, 0)),
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure", "aws_prod_admin", "Vikram Nair", "approved", ts(2025, 2, 10, 16, 30), ts(2025, 2, 11, 10, 0)),
    _event("ARUN01", "devops_cloud_engineer", "Cloud Infrastructure", "cyberark_pam", "Raj Kumar", "approved", ts(2025, 2, 15, 10, 0), ts(2025, 2, 15, 14, 0)),
]


def seed():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)

    print("Users:")
    db.executemany(
        """
        INSERT INTO users (acf2_id, name, team, manager, dept, employment_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        USERS,
    )
    for acf2_id, name, *_ in USERS:
        print(f"  seeded: {acf2_id} - {name}")

    print("\nDesignations:")
    db.executemany(
        """
        INSERT INTO designations (id, title, description, team_hint, dept_hint)
        VALUES (:id, :title, :description, :team_hint, :dept_hint)
        """,
        DESIGNATIONS,
    )
    for designation in DESIGNATIONS:
        print(f"  template: {designation['id']}")

    access_rows = list(role_access_rows())
    db.executemany(
        """
        INSERT INTO role_access_items
          (id, designation_id, access_item, display_name, system, description,
           mandatory, owner_team, servicenow_catalog_item_id, sort_order)
        VALUES
          (:id, :designation_id, :access_item, :display_name, :system, :description,
           :mandatory, :owner_team, :servicenow_catalog_item_id, :sort_order)
        """,
        access_rows,
    )
    print(f"\nRole access items: {len(access_rows)} rows")

    db.executemany(
        """
        INSERT INTO user_designations (acf2_id, designation_id, assigned_at, source)
        VALUES (:acf2_id, :designation_id, :assigned_at, :source)
        """,
        USER_DESIGNATIONS,
    )
    print("User designations: ARUN01 and NEHA02 seeded; SARA03 intentionally unmapped")

    db.executemany(
        """
        INSERT INTO dangerous_combinations
          (id, access_item_a, access_item_b, severity, reason)
        VALUES (:id, :access_item_a, :access_item_b, :severity, :reason)
        """,
        DANGEROUS_COMBINATIONS,
    )
    print(f"Dangerous combinations: {len(DANGEROUS_COMBINATIONS)}")

    db.executemany(
        """
        INSERT INTO privilege_edges (id, acf2_id, access_item, granted_at, granted_by)
        VALUES (:id, :acf2_id, :access_item, :granted_at, :granted_by)
        """,
        PRIVILEGE_EDGES,
    )
    print("Privilege edges: NEHA02 demo edges seeded")

    db.executemany(
        """
        INSERT INTO approver_routing
          (id, access_item, approver_name, approver_email, teams_webhook_url, team)
        VALUES (:id, :access_item, :approver_name, :approver_email, :teams_webhook_url, :team)
        """,
        APPROVER_ROUTING,
    )
    print(f"Approver routing: {len(APPROVER_ROUTING)} access items")

    db.executemany(
        """
        INSERT INTO approval_events
          (id, access_request_id, acf2_id, role, team, access_item,
           approver, status, submitted_at, resolved_at, off_hours)
        VALUES
          (:id, :access_request_id, :acf2_id, :role, :team, :access_item,
           :approver, :status, :submitted_at, :resolved_at, :off_hours)
        """,
        APPROVAL_EVENTS,
    )
    arun_events = sum(1 for event in APPROVAL_EVENTS if event["acf2_id"] == "ARUN01")
    print(f"Approval events: {len(APPROVAL_EVENTS)} rows ({arun_events} ARUN01 anomaly rows)")

    db.commit()
    db.close()
    print(f"\nDone. DB at: {DB_PATH}")


if __name__ == "__main__":
    seed()
