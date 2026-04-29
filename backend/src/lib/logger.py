"""
Color-coded logging utility — HackHERway PS6

Usage:
    from src.lib.logger import log, agent, bedrock, mcp, mock, teams, snow, orch, error

Prefixes: [AGENT] [BEDROCK] [MCP] [MOCK] [TEAMS] [SERVICENOW] [ORCHESTRATOR] [ERROR]
"""

from colorama import Fore, Style, init

init(autoreset=True)  # Windows-safe: reset ANSI codes after each print

_PREFIX_COLORS = {
    "AGENT":        Fore.CYAN,
    "BEDROCK":      Fore.YELLOW,
    "MCP":          Fore.BLUE,
    "MOCK":         Fore.MAGENTA,
    "TEAMS":        Fore.GREEN,
    "SERVICENOW":   Fore.GREEN,
    "ORCHESTRATOR": Fore.WHITE,
    "ERROR":        Fore.RED,
}


def log(prefix: str, message: str) -> None:
    """Print a color-coded log line with the given prefix."""
    color = _PREFIX_COLORS.get(prefix.upper(), Fore.WHITE)
    label = f"{color}[{prefix.upper()}]{Style.RESET_ALL}"
    print(f"{label}  {message}", flush=True)


# ── Convenience shortcuts ─────────────────────────────────────────────────────

def agent(msg: str) -> None:   log("AGENT", msg)
def bedrock(msg: str) -> None: log("BEDROCK", msg)
def mcp(msg: str) -> None:     log("MCP", msg)
def mock(msg: str) -> None:    log("MOCK", msg)
def teams(msg: str) -> None:   log("TEAMS", msg)
def snow(msg: str) -> None:    log("SERVICENOW", msg)
def orch(msg: str) -> None:    log("ORCHESTRATOR", msg)
def error(msg: str) -> None:   log("ERROR", msg)
