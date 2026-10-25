"""Pressure test for the agent team and the MCP tools. Does not call the model."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "mcp_server"))
sys.path.insert(0, str(ROOT / "backend"))

import tools  # noqa: E402
from team import MODEL_NAME, ROLES, blocked_task, load_prompt  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _balance(path: Path) -> float:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]
    finally:
        conn.close()


def _payment_count(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    finally:
        conn.close()


def check_tool_guardrails() -> None:
    original = ROOT / "data" / "campus_customs.db"
    working = ROOT / "data" / "campus_customs_new.db"
    before_original = _sha(original)
    before_working = _sha(working)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "shop.db"
        shutil.copy(original, copy)
        tools.DB_PATH = copy

        board = tools.list_open_tickets()
        assert board["shop_today"] == "2026-08-31"
        assert board["open_count"] == 3
        assert [row["id"] for row in board["tickets"]] == [101, 102, 103]

        refused = tools.pay_approved_obligation(102, "boss")
        assert refused["paid"] is False
        assert _payment_count(copy) == 0
        assert _balance(copy) == 3400.0

        no_bill = tools.pay_approved_obligation(103, "Board Chair")
        assert no_bill["paid"] is False
        assert _payment_count(copy) == 0

        conn = sqlite3.connect(copy)
        conn.execute("UPDATE cash_accounts SET balance = 100 WHERE name = 'checking'")
        conn.commit()
        conn.close()
        poor = tools.pay_approved_obligation(102, "Board Chair")
        assert poor["paid"] is False
        assert _balance(copy) == 100.0
        assert _payment_count(copy) == 0

        conn = sqlite3.connect(copy)
        conn.execute("UPDATE cash_accounts SET balance = 3400 WHERE name = 'checking'")
        conn.commit()
        conn.close()
        paid = tools.pay_approved_obligation(102, "Board Chair")
        assert paid["paid"] is True
        assert paid["amount"] == 2400.0
        assert paid["checking_balance"] == 1000.0
        assert paid["kind"] == "rent"
        again = tools.pay_approved_obligation(102, "Board Chair")
        assert again["paid"] is False
        assert _balance(copy) == 1000.0

        invoice = tools.pay_approved_obligation(101, "Board Chair")
        assert invoice["paid"] is True
        assert invoice["amount"] == 840.0
        assert invoice["checking_balance"] == 160.0
        status = sqlite3.connect(copy).execute("SELECT status FROM invoices WHERE id=501").fetchone()[0]
        assert status == "paid"

        draft = tools.save_board_draft(101, "customer_service", "Size S is not on the shelf yet.")
        assert draft["saved"] is True and draft["sent"] is False
        assert "[draft by customer_service]" in draft["notes"]
        assert "Needs a tee in size S." in draft["notes"]
        bad_role = tools.save_board_draft(101, "stranger", "hello")
        assert bad_role["saved"] is False

    tools.DB_PATH = working
    assert _sha(original) == before_original
    assert _sha(working) == before_working
    assert _payment_count(working) == 0


def check_team_files() -> None:
    for role in ROLES:
        text = load_prompt(role)
        assert "shop today" in text.lower() or "Shop today" in text
        assert role.replace("_", " ").split()[0].lower() in text.lower() or role in text
        assert (ROOT / "backend" / "prompts" / f"{role}.md").is_file()
    assert (ROOT / "backend" / "prompts" / "shop_rules.md").is_file()
    assert MODEL_NAME == "gpt-6-luna"
    agent_files = ["team.py", "mcp_client.py", "audit.py", "models.py", "run_team.py"]
    for name in agent_files:
        source = (ROOT / "backend" / name).read_text(encoding="utf-8")
        assert "sqlite3" not in source, name
        assert "campus_customs" not in source, name
    assert blocked_task("Do not email customers.") is None
    assert blocked_task("Please email the customer a tracking number.") is not None
    config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert "campus-customs" in config["mcpServers"]


def main() -> None:
    check_team_files()
    check_tool_guardrails()
    print("PRESSURE TEST OK")


if __name__ == "__main__":
    main()
