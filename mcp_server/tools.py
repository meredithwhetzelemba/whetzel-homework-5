"""Read-only shop lookups for the Campus Customs MCP server.

Every value comes from data/campus_customs_new.db. Comparisons such as
shortfall or "due before shop today" are arithmetic on those stored
fields. Shop today is desk.date_today, never the computer clock.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"


def connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _shop_today(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    if row is None:
        return None
    return row["date_today"]


def _before(left: str | None, right: str | None) -> bool | None:
    """True when both stored YYYY-MM-DD values exist and left is earlier."""
    if left is None or right is None:
        return None
    return left < right


def _ticket_or_error(conn: sqlite3.Connection, ticket_id: int, expected_type: str) -> sqlite3.Row | dict:
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        return {
            "ticket_id": ticket_id,
            "found": False,
            "detail": "No row in tickets with this id.",
        }
    if row["type"] != expected_type:
        return {
            "ticket_id": row["id"],
            "found": True,
            "applicable": False,
            "ticket_type": row["type"],
            "expected_type": expected_type,
            "detail": (
                f"Ticket {row['id']} is type {row['type']}. "
                f"This tool only reads {expected_type} tickets."
            ),
        }
    return row


def lookup_order_stock_and_reprint_invoice(ticket_id: int) -> dict:
    """Read a customer_order ticket, the size on the shelf, and its vendor invoice.

    Use this for an order that may be blocked by a stockout and an unpaid
    reprint bill. Reads tickets, inventory (same sku and size), invoices
    (tickets.invoice_id), vendors (invoices.vendor_id), and desk.date_today.
    Does not invent a ship date or a payment.
    """
    with connect() as conn:
        ticket = _ticket_or_error(conn, ticket_id, "customer_order")
        if isinstance(ticket, dict):
            return ticket

        item = conn.execute(
            """
            SELECT name, qty, location
            FROM inventory
            WHERE sku = ? AND size = ?
            """,
            (ticket["sku"], ticket["size"]),
        ).fetchone()
        invoice = None
        vendor = None
        vendor_open_invoice_count = None
        if ticket["invoice_id"] is not None:
            invoice = conn.execute(
                """
                SELECT id, vendor_id, amount, due_date, status, description
                FROM invoices
                WHERE id = ?
                """,
                (ticket["invoice_id"],),
            ).fetchone()
            if invoice is not None:
                vendor = conn.execute(
                    """
                    SELECT id, name, specialty, lead_days
                    FROM vendors
                    WHERE id = ?
                    """,
                    (invoice["vendor_id"],),
                ).fetchone()
                vendor_open_invoice_count = conn.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM invoices
                    WHERE vendor_id = ? AND status = 'open'
                    """,
                    (invoice["vendor_id"],),
                ).fetchone()["n"]

        shop_today = _shop_today(conn)

    on_hand = None if item is None else item["qty"]
    requested = ticket["qty"]
    shortfall = None
    if on_hand is not None and requested is not None:
        shortfall = max(0, requested - on_hand)

    due_date = None if invoice is None else invoice["due_date"]
    return {
        "found": True,
        "applicable": True,
        "ticket_id": ticket["id"],
        "ticket_type": ticket["type"],
        "status": ticket["status"],
        "requester": ticket["requester"],
        "subject": ticket["subject"],
        "notes": ticket["notes"],
        "sku": ticket["sku"],
        "size": ticket["size"],
        "requested_qty": requested,
        "item_name": None if item is None else item["name"],
        "on_hand_qty": on_hand,
        "location": None if item is None else item["location"],
        "shortfall": shortfall,
        "invoice_id": ticket["invoice_id"],
        "invoice_amount": None if invoice is None else invoice["amount"],
        "invoice_due_date": due_date,
        "invoice_status": None if invoice is None else invoice["status"],
        "invoice_description": None if invoice is None else invoice["description"],
        "shop_today": shop_today,
        "invoice_due_before_shop_today": _before(due_date, shop_today),
        "vendor_id": None if vendor is None else vendor["id"],
        "vendor_name": None if vendor is None else vendor["name"],
        "vendor_specialty": None if vendor is None else vendor["specialty"],
        "vendor_lead_days": None if vendor is None else vendor["lead_days"],
        "vendor_open_invoice_count": vendor_open_invoice_count,
    }


def lookup_rent_due_against_cash(ticket_id: int) -> dict:
    """Read a rent_notice ticket, its lease, and whether checking can cover rent.

    Use this before anyone approves a rent payment. Reads tickets,
    leases (tickets.lease_id), cash_accounts, payments whose ref_id equals
    that lease id, and desk.date_today. Does not record a payment or change
    the balance. cash_after_rent is balance minus monthly_rent, computed
    here and not written to the database.
    """
    with connect() as conn:
        ticket = _ticket_or_error(conn, ticket_id, "rent_notice")
        if isinstance(ticket, dict):
            return ticket

        lease = None
        payment_rows: list[sqlite3.Row] = []
        if ticket["lease_id"] is not None:
            lease = conn.execute(
                """
                SELECT id, space_name, landlord, monthly_rent, next_due, notes
                FROM leases
                WHERE id = ?
                """,
                (ticket["lease_id"],),
            ).fetchone()
            payment_rows = conn.execute(
                """
                SELECT id, kind, ref_id, amount, account, paid_at, approved_by
                FROM payments
                WHERE ref_id = ?
                ORDER BY id
                """,
                (ticket["lease_id"],),
            ).fetchall()

        accounts = conn.execute(
            "SELECT name, balance, date FROM cash_accounts ORDER BY name"
        ).fetchall()
        shop_today = _shop_today(conn)

    checking = next((row for row in accounts if row["name"] == "checking"), None)
    monthly_rent = None if lease is None else lease["monthly_rent"]
    balance = None if checking is None else checking["balance"]
    cash_covers_rent = None
    cash_after_rent = None
    if balance is not None and monthly_rent is not None:
        cash_covers_rent = balance >= monthly_rent
        cash_after_rent = balance - monthly_rent

    next_due = None if lease is None else lease["next_due"]
    return {
        "found": True,
        "applicable": True,
        "ticket_id": ticket["id"],
        "ticket_type": ticket["type"],
        "status": ticket["status"],
        "requester": ticket["requester"],
        "subject": ticket["subject"],
        "notes": ticket["notes"],
        "lease_id": ticket["lease_id"],
        "space_name": None if lease is None else lease["space_name"],
        "landlord": None if lease is None else lease["landlord"],
        "monthly_rent": monthly_rent,
        "next_due": next_due,
        "lease_notes": None if lease is None else lease["notes"],
        "shop_today": shop_today,
        "rent_due_before_shop_today": _before(next_due, shop_today),
        "cash_accounts": [
            {"name": row["name"], "balance": row["balance"], "date": row["date"]}
            for row in accounts
        ],
        "checking_balance": balance,
        "checking_as_of": None if checking is None else checking["date"],
        "cash_covers_monthly_rent": cash_covers_rent,
        "cash_after_rent": cash_after_rent,
        "payments_with_this_lease_ref": [
            {
                "id": row["id"],
                "kind": row["kind"],
                "ref_id": row["ref_id"],
                "amount": row["amount"],
                "account": row["account"],
                "paid_at": row["paid_at"],
                "approved_by": row["approved_by"],
            }
            for row in payment_rows
        ],
    }


def lookup_bulk_discount_margin(ticket_id: int) -> dict:
    """Read a price_override ticket, size-level stock, and list-versus-cost margin.

    Use this when a buyer wants a bulk discount. Reads tickets, inventory
    for that sku and size only, and pricing for that sku. The database does
    not store a requested discount percent, so this tool does not invent one.
    list_margin_per_unit is list_price minus unit_cost.
    """
    with connect() as conn:
        ticket = _ticket_or_error(conn, ticket_id, "price_override")
        if isinstance(ticket, dict):
            return ticket

        item = conn.execute(
            """
            SELECT name, qty, location
            FROM inventory
            WHERE sku = ? AND size = ?
            """,
            (ticket["sku"], ticket["size"]),
        ).fetchone()
        price = None
        if ticket["sku"] is not None:
            price = conn.execute(
                """
                SELECT sku, unit_cost, list_price
                FROM pricing
                WHERE sku = ?
                """,
                (ticket["sku"],),
            ).fetchone()

    on_hand = None if item is None else item["qty"]
    requested = ticket["qty"]
    shortfall = None
    fillable_from_shelf = None
    if on_hand is not None and requested is not None:
        shortfall = max(0, requested - on_hand)
        fillable_from_shelf = min(on_hand, requested)

    unit_cost = None if price is None else price["unit_cost"]
    list_price = None if price is None else price["list_price"]
    list_margin_per_unit = None
    list_extended = None
    cost_extended = None
    if unit_cost is not None and list_price is not None:
        list_margin_per_unit = list_price - unit_cost
    if list_price is not None and requested is not None:
        list_extended = list_price * requested
    if unit_cost is not None and requested is not None:
        cost_extended = unit_cost * requested

    return {
        "found": True,
        "applicable": True,
        "ticket_id": ticket["id"],
        "ticket_type": ticket["type"],
        "status": ticket["status"],
        "requester": ticket["requester"],
        "subject": ticket["subject"],
        "notes": ticket["notes"],
        "sku": ticket["sku"],
        "size": ticket["size"],
        "requested_qty": requested,
        "item_name": None if item is None else item["name"],
        "on_hand_qty": on_hand,
        "location": None if item is None else item["location"],
        "shortfall": shortfall,
        "fillable_from_shelf": fillable_from_shelf,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "list_margin_per_unit": list_margin_per_unit,
        "list_extended": list_extended,
        "cost_extended": cost_extended,
    }


ROLES = ("boss", "inventory", "accounting", "facilities", "customer_service")
BLOCKED_APPROVERS = {
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
    "customer service",
    "agent",
    "system",
    "auto",
    "mcp",
    "human",
}


def connect_write() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def list_board_tickets() -> dict:
    """Return every ticket and whether its status is open or resolved.

    The desk uses this so a resolved ticket stays on the board. Reads tickets
    and desk. Does not change the database.
    """
    with connect() as conn:
        shop_today = _shop_today(conn)
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            ORDER BY id
            """
        ).fetchall()
    tickets = []
    for row in rows:
        status = row["status"]
        tickets.append(
            {
                "id": row["id"],
                "type": row["type"],
                "requester": row["requester"],
                "subject": row["subject"],
                "sku": row["sku"],
                "size": row["size"],
                "qty": row["qty"],
                "lease_id": row["lease_id"],
                "invoice_id": row["invoice_id"],
                "status": status,
                "state": "open" if status == "open" else "resolved",
                "notes": row["notes"],
                "created_at": row["created_at"],
            }
        )
    return {"shop_today": shop_today, "tickets": tickets}


def resolve_ticket(ticket_id: int) -> dict:
    """Mark one ticket resolved after the team finishes its run.

    Updates tickets.status. Does not move cash and does not send a message.
    """
    with connect_write() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT id, status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"resolved": False, "ticket_id": ticket_id, "reason": "No ticket with that id."}
        conn.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket_id,))
        conn.commit()
    return {"resolved": True, "ticket_id": ticket_id, "status": "resolved", "state": "resolved"}


def get_checking_balance() -> dict:
    """Return the checking row from cash_accounts. Does not change the balance."""
    with connect() as conn:
        row = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()
    if row is None:
        return {"found": False, "name": "checking", "balance": None, "date": None}
    return {
        "found": True,
        "name": row["name"],
        "balance": row["balance"],
        "date": row["date"],
    }


def list_open_tickets() -> dict:
    """List every open ticket on the board, plus shop today from desk.

    Boss uses this to see the work before assigning it. Reads tickets and
    desk. Does not invent tickets and does not change the database.
    """
    with connect() as conn:
        shop_today = _shop_today(conn)
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, sku, size, qty,
                   lease_id, invoice_id, status, notes, created_at
            FROM tickets
            WHERE status = 'open'
            ORDER BY id
            """
        ).fetchall()
    tickets = [
        {
            "id": row["id"],
            "type": row["type"],
            "requester": row["requester"],
            "subject": row["subject"],
            "sku": row["sku"],
            "size": row["size"],
            "qty": row["qty"],
            "lease_id": row["lease_id"],
            "invoice_id": row["invoice_id"],
            "status": row["status"],
            "notes": row["notes"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return {"shop_today": shop_today, "open_count": len(tickets), "tickets": tickets}


def save_board_draft(ticket_id: int, author_role: str, draft: str) -> dict:
    """Append a draft to a ticket's notes. This does not email or call anyone.

    Customer Service uses this so a customer message stays on the board.
    Reads and updates tickets only. author_role must be one of the five
    shop roles. The original note is kept; the draft is appended after it.
    """
    role = (author_role or "").strip().lower().replace(" ", "_")
    text = (draft or "").strip()
    if role not in ROLES:
        return {
            "saved": False,
            "ticket_id": ticket_id,
            "reason": "author_role must be one of the five shop roles.",
        }
    if not text:
        return {"saved": False, "ticket_id": ticket_id, "reason": "Draft text is empty."}

    with connect_write() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT id, notes, status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"saved": False, "ticket_id": ticket_id, "reason": "No ticket with that id."}
        existing = row["notes"] or ""
        updated = existing.rstrip() + f"\n\n[draft by {role}]\n{text}"
        conn.execute("UPDATE tickets SET notes = ? WHERE id = ?", (updated, ticket_id))
        conn.commit()
    return {
        "saved": True,
        "ticket_id": ticket_id,
        "author_role": role,
        "sent": False,
        "notes": updated,
    }


def pay_approved_obligation(ticket_id: int, approved_by: str) -> dict:
    """Pay the database obligation on a ticket after a human approves it.

    The amount is read from invoices or leases. This tool does not accept an
    amount argument. It refuses when approved_by is blank or is an agent role,
    when checking cannot cover the stored amount, or when that bill is already
    paid. On success it inserts payments, decreases cash_accounts, and marks
    an invoice paid. Cash is never allowed to go negative.
    """
    approver = " ".join((approved_by or "").split())
    if len(approver) < 2 or approver.lower() in BLOCKED_APPROVERS:
        return {
            "paid": False,
            "ticket_id": ticket_id,
            "reason": "A human approver name is required. Agent roles cannot approve a payment.",
        }

    with connect_write() as conn:
        conn.execute("BEGIN IMMEDIATE")
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            conn.rollback()
            return {"paid": False, "ticket_id": ticket_id, "reason": "No ticket with that id."}

        shop_today = _shop_today(conn)
        kind = None
        ref_id = None
        amount = None
        description = None

        if ticket["type"] == "customer_order":
            if ticket["invoice_id"] is None:
                conn.rollback()
                return {"paid": False, "ticket_id": ticket_id, "reason": "This order has no invoice to pay."}
            invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (ticket["invoice_id"],)).fetchone()
            if invoice is None:
                conn.rollback()
                return {"paid": False, "ticket_id": ticket_id, "reason": "Linked invoice row is missing."}
            if invoice["status"] != "open":
                conn.rollback()
                return {
                    "paid": False,
                    "ticket_id": ticket_id,
                    "reason": f"Invoice {invoice['id']} status is {invoice['status']}.",
                }
            kind = "invoice"
            ref_id = invoice["id"]
            amount = invoice["amount"]
            description = invoice["description"]
        elif ticket["type"] == "rent_notice":
            if ticket["lease_id"] is None:
                conn.rollback()
                return {"paid": False, "ticket_id": ticket_id, "reason": "This rent notice has no lease."}
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
            if lease is None:
                conn.rollback()
                return {"paid": False, "ticket_id": ticket_id, "reason": "Linked lease row is missing."}
            kind = "rent"
            ref_id = lease["id"]
            amount = lease["monthly_rent"]
            description = lease["space_name"]
        else:
            conn.rollback()
            return {
                "paid": False,
                "ticket_id": ticket_id,
                "ticket_type": ticket["type"],
                "reason": "This ticket type has no payable obligation in the database.",
            }

        already = conn.execute(
            "SELECT id FROM payments WHERE kind = ? AND ref_id = ?",
            (kind, ref_id),
        ).fetchone()
        if already is not None:
            conn.rollback()
            return {
                "paid": False,
                "ticket_id": ticket_id,
                "reason": f"A {kind} payment for ref {ref_id} already exists.",
            }

        cash = conn.execute(
            "SELECT name, balance FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()
        if cash is None:
            conn.rollback()
            return {"paid": False, "ticket_id": ticket_id, "reason": "No checking account."}
        if cash["balance"] < amount:
            conn.rollback()
            return {
                "paid": False,
                "ticket_id": ticket_id,
                "amount": amount,
                "checking_balance": cash["balance"],
                "reason": "Checking cannot cover this payment. Balance was not changed.",
            }

        updated = conn.execute(
            """
            UPDATE cash_accounts
            SET balance = balance - ?, date = ?
            WHERE name = 'checking' AND balance >= ?
            """,
            (amount, shop_today, amount),
        )
        if updated.rowcount != 1:
            conn.rollback()
            return {
                "paid": False,
                "ticket_id": ticket_id,
                "reason": "Checking could not be debited. No payment was recorded.",
            }
        conn.execute(
            """
            INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
            VALUES (?, ?, ?, 'checking', ?, ?)
            """,
            (kind, ref_id, amount, shop_today, approver),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        balance = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()["balance"]
        conn.commit()

    return {
        "paid": True,
        "ticket_id": ticket_id,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "description": description,
        "account": "checking",
        "paid_at": shop_today,
        "approved_by": approver,
        "checking_balance": balance,
    }
