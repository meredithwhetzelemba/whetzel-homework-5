# Campus Customs MCP server

This server is the tool layer for the Campus Customs agent team. Boss, Inventory, Accounting, Facilities, and Customer Service call these tools instead of guessing what is on the shelf, what a bill says, or how much cash is in the register.

It reads and, for two tools, updates the working database only:

`data/campus_customs_new.db`

`data/campus_customs.db` stays the untouched original. Shop today is `desk.date_today` from the working file. The agent team does not open this database itself. It calls these tools over the stdio connection in `.mcp.json`.

The server is built with FastMCP (`from fastmcp import FastMCP`). Start it from this folder with:

```bash
python server.py
```

## Tools

| Tool | Tables | What it does |
|------|--------|----------------|
| `list_board_tickets` | `tickets`, `desk` | Returns every ticket, including ones that are no longer open, with open or resolved. |
| `get_checking_balance` | `cash_accounts` | Returns the checking balance and its date. Does not change cash. |
| `list_open_tickets` | `tickets`, `desk` | Returns every open ticket and shop today so Boss can assign work. |
| `lookup_order_stock_and_reprint_invoice` | `tickets`, `inventory`, `invoices`, `vendors`, `desk` | Ticket 101: size-level stock, the linked reprint invoice, and that vendor's lead time. |
| `lookup_rent_due_against_cash` | `tickets`, `leases`, `cash_accounts`, `payments`, `desk` | Ticket 102: rent amount, due date, and whether checking can cover it. |
| `lookup_bulk_discount_margin` | `tickets`, `inventory`, `pricing` | Ticket 103: size M on hand, unit cost, and list price. No discount percent is stored. |
| `save_board_draft` | `tickets` | Appends a draft to the ticket notes. It does not email or call anyone. |
| `pay_approved_obligation` | `tickets`, `invoices`, `leases`, `cash_accounts`, `payments`, `desk` | Pays the stored invoice or rent only when a human approver is named. Refuses if checking would go negative. |
| `resolve_ticket` | `tickets` | Sets one ticket's status to resolved after the desk run finishes. Does not move cash. |

Lookup tools take a `ticket_id`. If that id is missing, or the ticket is a different type, the tool says so from the `tickets` row and does not fill in other tables. `pay_approved_obligation` does not take an amount; it uses the invoice or lease row.
