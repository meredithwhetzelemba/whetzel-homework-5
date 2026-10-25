# Campus Customs

The night desk for a campus shop. An MCP server reads the shop database, a FastAPI backend runs five agents (Boss, Inventory, Accounting, Facilities, and Customer Service), and a React board lets a person watch the run and sign a payment.

Shop today is `desk.date_today` in the database (`2026-08-31`), not the clock on the computer. Agents prepare payments. They do not move cash. The human approve button does. Drafts stay on the ticket. Nothing is emailed.

The model for every agent is `gpt-6-luna` through Portkey. Put the key in a local `.env`. Do not commit that file.

## Layout

```
AI_prompts.md
requirements.txt
.env.example
.gitignore
.mcp.json
README.md
data/campus_customs.db
data/campus_customs_new.db
mcp_server/server.py
mcp_server/README.md
frontend/
backend/main.py
backend/models.py
backend/prompts/
output/
```

`data/campus_customs.db` is the original shop. `data/campus_customs_new.db` is the working copy. The copy in this repo is the sitting after tickets 101, 102, and 103 were resolved: checking is $160.00, invoice 501 is paid, and the rent payment is recorded. Reset before you run the three tickets again.

## Setup

Use Python 3.12. The agents need `pydantic-ai-slim[openai]`, which current 3.9 installs will not satisfy.

```bash
cd mcp_server
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
cd ../backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
cp ../.env.example .env
```

Edit `backend/.env` and set `PORTKEY_API_KEY`. Leave `OPENAI_MODEL=gpt-6-luna`.

```bash
cd ../frontend
npm install
```

`.mcp.json` starts the MCP server with `mcp_server/.venv/bin/python`. Paths in that file are relative to this repo. The backend turns them into absolute paths when it connects, so you can start uvicorn from `backend/`.

## Clean the working database

Copy the original over the working copy whenever you want the shop back to the start (checking $3,400.00, three open tickets, no payments):

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Do that before a full three-ticket run. With the backend already up, the same reset is `POST http://localhost:8000/reset`, or the **Reset the book** control on the React desk. Reset does not wipe `output/audit_trail.json`.

## Start the MCP server

The server speaks stdio. The backend starts it from `.mcp.json` when a route needs shop data. You do not leave a second copy running.

To confirm the process itself starts, from `mcp_server/` with its venv active:

```bash
python server.py
```

That waits for MCP messages on stdin. Stop it with Ctrl-C. Normal use is the backend launching it.

## Start the FastAPI backend

From `backend/`, with that venv active:

```bash
uvicorn main:app --reload --port 8000
```

The API is at `http://localhost:8000`. It allows the Vite origin `http://localhost:5173`.

## Start the React board

From `frontend/`:

```bash
npm run dev
```

Open `http://localhost:5173`. The board lists tickets 101, 102, and 103, runs the team on the one you pick, and shows each agent while the run is in flight. When the run finishes, the ticket is marked handled. If the team asks for a payment, sign with your name. Checking updates from `GET /cash`.

Before you run all three tickets yourself, reset the working database with the copy command above, or with **Reset the book**. Note the checking balance after the reset. It should be $3,400.00.

## What the output folder is

`output/desk_tickets.html` is the plan, the actual runs, the cash tab, and the reflection. `output/resolved_board.html` is the desk screenshots. `output/resolved_tickets.json` is the per-ticket record. `output/audit_trail.json` is append-only. `output/github_url.txt` is this repository.
