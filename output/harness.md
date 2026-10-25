# Campus Customs Multi-Agent Operations — Harness (Homework 5)

**Audience:** a manager or teammate who needs to see how the agent team is controlled. This file starts with the shop database and will grow in later problems (tools, delegation, approvals, safety, and limits).

**In one sentence:** open tickets land on a board, and Boss, Inventory, Accounting, Facilities, and Customer Service work them using the shop database — never invented stock, cash, or dates.

**Original database (do not edit):** `data/campus_customs.db`  
**Working copy (later problems update this):** `data/campus_customs_new.db`  
**Shop “today”:** `desk.date_today` = `2026-08-31`

Both files started identical. Reset a run by copying the original over the working copy.

---

## 1. Database overview

Nine tables. Three tickets are open. `payments` is empty. One invoice is open and already overdue.

| Table | Rows now | Why this table matters for the agents |
|-------|----------|----------------------------------------|
| `desk` | 1 | Agents must treat `date_today` as the shop’s today when they decide what is overdue. |
| `tickets` | 3 | This is the work board: Boss reads each row, assigns it, and later marks it resolved. |
| `inventory` | 10 | Inventory checks real on-hand quantity by SKU and size before anyone promises an item. |
| `pricing` | 4 | Accounting uses cost and list price to judge a discount and the margin on a sale. |
| `vendors` | 3 | Inventory uses specialty and lead time to see who can restock, and how long it takes. |
| `leases` | 1 | Facilities reads the space, landlord, rent amount, and next due date. |
| `cash_accounts` | 1 | Accounting must refuse a payment that would push this balance below zero. |
| `payments` | 0 | A payment is recorded here only after a human approves it. |
| `invoices` | 1 | Accounting watches unpaid vendor bills; a vendor will not ship while one of theirs is still open. |

---

## 2. Table: `desk`

| Field | Type | Notes |
|-------|------|--------|
| `date_today` | TEXT, required | Shop today. Currently `2026-08-31`. |
| `notes` | TEXT | Optional desk note. Empty right now. |

Agents use this date instead of the computer’s clock. Overdue means `due_date` or `next_due` is before `date_today`.

---

## 3. Table: `tickets`

| Field | Type | Notes |
|-------|------|--------|
| `id` | INTEGER, primary key | Ticket number on the board (101, 102, 103). |
| `type` | TEXT, required | `customer_order`, `rent_notice`, or `price_override`. |
| `requester` | TEXT, required | Who opened it. |
| `subject` | TEXT, required | Short title. |
| `sku` | TEXT | Item, when the ticket is about merchandise. |
| `size` | TEXT | Size, paired with `sku`. |
| `qty` | INTEGER | How many the requester wants. |
| `lease_id` | INTEGER, foreign key → `leases.id` | Set when the ticket is about the shop space. |
| `invoice_id` | INTEGER, foreign key → `invoices.id` | Set when the ticket is tied to a vendor bill. |
| `status` | TEXT, required | All three are `open`. |
| `notes` | TEXT | Extra detail from the requester. |
| `created_at` | TEXT, required | When the ticket was opened. |

Boss starts here. The optional `sku`, `lease_id`, and `invoice_id` fields are how a ticket points at the rest of the shop.

---

## 4. Table: `inventory`

| Field | Type | Notes |
|-------|------|--------|
| `sku` | TEXT, required | Item code. Part of the primary key. |
| `name` | TEXT, required | Product name. |
| `size` | TEXT, required | Size, including `OS` for one-size goods. Part of the primary key. |
| `qty` | INTEGER, required | Units on the shelf. `0` means that size is out. |
| `location` | TEXT, required | Aisle. |

Primary key is `(sku, size)`. A ticket’s `sku` + `size` matches one row here.

---

## 5. Table: `pricing`

| Field | Type | Notes |
|-------|------|--------|
| `sku` | TEXT, primary key | Same item code as `inventory.sku`. |
| `unit_cost` | REAL, required | What the shop pays per unit. |
| `list_price` | REAL, required | Normal selling price per unit. |

One price row per SKU, not per size. Margin is `list_price - unit_cost`.

---

## 6. Table: `vendors`

| Field | Type | Notes |
|-------|------|--------|
| `id` | INTEGER, primary key | Vendor id. `invoices.vendor_id` points here. |
| `name` | TEXT, required | Vendor name. |
| `specialty` | TEXT, required | What they supply (apparel reprint, mugs, courier). |
| `lead_days` | INTEGER, required | How many days until a new shipment can arrive. |

A vendor with an open unpaid invoice must not be treated as able to ship.

---

## 7. Table: `leases`

| Field | Type | Notes |
|-------|------|--------|
| `id` | INTEGER, primary key | Lease id. `tickets.lease_id` points here. |
| `space_name` | TEXT, required | Which space. |
| `landlord` | TEXT, required | Who is owed rent. |
| `monthly_rent` | REAL, required | Amount due. |
| `next_due` | TEXT, required | Next rent date, compared with `desk.date_today`. |
| `notes` | TEXT | Optional. Empty right now. |

---

## 8. Table: `cash_accounts`

| Field | Type | Notes |
|-------|------|--------|
| `name` | TEXT, primary key | Account name. `payments.account` should match this. |
| `balance` | REAL, required | Cash on hand. Currently `3400.0` in `checking`. |
| `date` | TEXT, required | Date of that balance. Currently `2026-08-31`. |

Cash only goes out in this homework. A pay action that would make `balance` negative must be refused.

---

## 9. Table: `payments`

| Field | Type | Notes |
|-------|------|--------|
| `id` | INTEGER, primary key | Payment id. No rows yet. |
| `kind` | TEXT, required | What was paid (for example rent or a vendor invoice). |
| `ref_id` | INTEGER | Id of the lease, invoice, or other row this payment covers. |
| `amount` | REAL, required | Dollars paid. |
| `account` | TEXT, required | Which cash account the money left. |
| `paid_at` | TEXT, required | When it was paid. |
| `approved_by` | TEXT, required | The human who approved it. Required on every payment. |

Empty until a person approves a payment and the working database is updated.

---

## 10. Table: `invoices`

| Field | Type | Notes |
|-------|------|--------|
| `id` | INTEGER, primary key | Invoice id. `tickets.invoice_id` points here. |
| `vendor_id` | INTEGER, required, foreign key → `vendors.id` | Who is owed. |
| `amount` | REAL, required | Amount due. |
| `due_date` | TEXT, required | Compared with `desk.date_today`. |
| `status` | TEXT, required | `open` until it is paid. |
| `description` | TEXT | What the bill is for. |

The only invoice is 501: **$840** to Bulldog Print Co, due **2026-08-28**, status **open** (“Rush reprint CC-TEE-WHITE S”). That due date is before shop today, so it is overdue.

---

## 11. MCP tools (`mcp_server/`)

The FastMCP server reads `data/campus_customs_new.db` only. These three tools are the first ones every agent will call. Later problems can add more. None of them write to the database.

### `lookup_order_stock_and_reprint_invoice`

- **Reads:** `tickets`, `inventory`, `invoices`, `vendors`, `desk`
- **Unlocks ticket:** 101
- **Why this tool:** Ticket 101 asks for one `CC-TEE-WHITE` in size S, and that size’s inventory quantity is 0, while `invoice_id` 501 is still an open $840 rush-reprint bill to Bulldog Print Co due 2026-08-28 — before shop today — so the order cannot be promised until that linked bill and the vendor’s 5-day lead time are visible together.

### `lookup_rent_due_against_cash`

- **Reads:** `tickets`, `leases`, `cash_accounts`, `payments`, `desk`
- **Unlocks ticket:** 102
- **Why this tool:** Ticket 102 is Elm City Properties’ rent notice for lease 1, and the decision is whether the $2,400 due 2026-09-02 (two days after shop today, so not overdue) can leave checking’s $3,400 without going negative, and that no payment row already points at that lease.

### `lookup_bulk_discount_margin`

- **Reads:** `tickets`, `inventory`, `pricing`
- **Unlocks ticket:** 103
- **Why this tool:** Ticket 103 is Yale AI Club asking to discount 20 `CC-HOOD-NAVY` size M hoodies when only 8 of that size are on the shelf, so Accounting needs the $22 unit cost, the $58 list price, and the 12-unit shortfall on size M — not the other sizes — before anyone names a discount the database never stored.

### `list_open_tickets`

- **Tables:** `tickets`, `desk`
- **Why this tool:** Boss cannot assign ticket 101, 102, or 103 until the tool returns those three open rows and shop today `2026-08-31`, instead of a remembered list.

### `save_board_draft`

- **Tables:** `tickets` (read and update)
- **Why this tool:** Customer Service can leave wording on a ticket, including Tauhid's tee order or the Yale AI Club hoodie request, while the tool's `sent` flag stays false so the draft is not an email.

### `pay_approved_obligation`

- **Tables:** `tickets`, `invoices`, `leases`, `cash_accounts`, `payments`, `desk`
- **Why this tool:** Ticket 101's $840 invoice and ticket 102's $2,400 rent can leave checking only when a human name is supplied, the amount is the stored bill, and the balance would not go negative. Ticket 103 has no payable row, so the tool refuses it.

### `resolve_ticket`

- **Tables:** `tickets` (read and update)
- **Why this tool:** After a run finishes without a refusal, the desk marks that ticket `resolved` so a refresh still shows Handled. Agents do not hold this tool. Reset copies the original database back, so the three tickets open again.

---

## 12. Agent team (`backend/`)

Every role loads `backend/prompts/shop_rules.md` plus its own file. The model for every role is `gpt-6-luna` through Portkey (`PORTKEY_API_KEY`). Shop facts come only from the MCP tools above. There is no second database layer in `backend/`.

Any role may delegate to any other role (`ask_boss`, `ask_inventory`, `ask_accounting`, `ask_facilities`, `ask_customer_service`). A role cannot ask itself. Delegation stops at depth 2. Each role call stops after 5 model requests.

Each agent loop step is appended to `output/audit_trail.json` (time, run id, role, iteration, node, thoughts, tool name, tool args, short result, stop reason). The file is never wiped.

| Agent | Prompt | What this role owns |
|-------|--------|---------------------|
| Boss | `backend/prompts/boss.md` | Reads the open board, assigns each ticket, and states the final call. |
| Inventory | `backend/prompts/inventory.md` | Size-level stock, shortfall, vendor specialty, lead days, and the unpaid-invoice ship block. |
| Accounting | `backend/prompts/accounting.md` | Invoice and rent amounts, margin at list, checking balance, and the human-approved pay tool. |
| Facilities | `backend/prompts/facilities.md` | Chapel Street lease, landlord, rent due date versus shop today. |
| Customer Service | `backend/prompts/customer_service.md` | Customer drafts saved on the ticket. No email is sent. |

---

## 13. Safety and token limits

Guardrails a shop would want when agents can see customers and move money:

- No tool sends email or places a call. `save_board_draft` only appends notes and returns `sent: false`.
- `pay_approved_obligation` ignores any amount the model might wish for. It pays the invoice or lease figure, and only after `approved_by` is a human name rather than a role name.
- The same tool refuses when checking cannot cover the bill, and it does not write a payment in that case.
- Cash only decreases. The tools never insert revenue.
- Ticket notes are data. A note that says "Email:" does not authorize sending mail, and a note that says to ignore the rules is refused.
- Secrets and the system prompt are out of scope. The audit log redacts key-shaped text.

Limits that keep a five-agent conversation from running away:

- 5 model requests per role call.
- Delegation depth 2, so Boss can ask a specialist and that specialist can ask one more role, then the chain stops.
- Output retries are capped at 1.
- Audit lines store a short result, not the full transcript.
- Agents prepare a payment. They do not hold `pay_approved_obligation`. `POST /tickets/{ticket_id}/approve` is the human click that moves cash.

---

## 14. Desk API (`backend/main.py`)

Start it from the `backend/` folder with `uvicorn main:app --reload --port 8000`. The dashboard calls `http://localhost:8000`. Ticket lists, the checking balance, and the payment all go through the MCP server. Reset copies `data/campus_customs.db` over `data/campus_customs_new.db`.

- `GET /tickets` — returns tickets 101, 102, and 103 and whether each status is open or resolved.
- `POST /tickets/{ticket_id}/run` — runs the agent team on that ticket; the team prepares work and does not pay. If the run is not refused, the route marks that ticket resolved.
- `GET /events` — recent audit rows: which agent spoke and which tool it used, so the board can refresh.
- `POST /tickets/{ticket_id}/approve` — a human name in the body; this is the call that pays the stored bill and changes checking.
- `GET /cash` — the current checking balance and date from `cash_accounts`.
- `POST /reset` — puts the working database back to the original shop values.

---

## 15. Dashboard (`frontend/`)

The desk is a React + Vite + TypeScript page. `npm run dev` serves it at `http://localhost:5173`. Every call goes to `http://localhost:8000`: `GET /tickets`, `POST /tickets/{id}/run`, `GET /events` while a run is in flight, `POST /tickets/{id}/approve` with a human name, `GET /cash`, and `POST /reset`.

The look is the night desk in `output/design.md`: near-black blotter, cream ticket paper, Fraunces for the title and the checking figure, lipstick pink only on the run button, the selected ticket, and the Handled stamp. The five plates do not share a skin. Boss is the ink plate, Inventory is the shelf, Accounting speaks in figures, Facilities is a dashed lease line, and Customer Service is an italic note.

A finished run that is not refused calls MCP `resolve_ticket`, so a refresh still shows Handled. Agents do not hold that tool and do not hold `pay_approved_obligation`. The checking figure updates from `GET /cash` after a human approves.

The Problem 9 sitting, after a reset, is recorded in `output/desk_tickets.html` (Actual and Cash), `output/resolved_tickets.json`, and `output/resolved_board.html`. Starting checking was $3,400.00. Ticket 101 paid invoice 501 for $840.00. Ticket 102 paid lease 1 rent for $2,400.00. Ticket 103 paid nothing. Ending checking is $160.00, which is the `cash_accounts` checking balance. All three ticket statuses are `resolved`. The runs were appended to `output/audit_trail.json` as `team_e21565a54f`, `team_ad0bf5677a`, and `team_0e9ceebd8e`.
