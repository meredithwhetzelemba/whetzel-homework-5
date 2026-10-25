# AI Prompts Log (Homework 5)

Log of prompts typed to the vibe coder (Cursor agent). Separate from any runtime prompt files that scripts may read later.

**Project context:** Campus Customs Multi-Agent Operations is the agentic team that runs the shop. Open tickets land on a board — customer orders, rent, unpaid bills, discount requests, and whatever else the shop has to handle. The build is three pieces that talk to each other: an MCP server, a FastAPI backend with a multi-agent team, and a React dashboard so a human can watch the agents and approve requests. The team has full connectivity: any agent may delegate to any other agent. Agents are Boss (reads each ticket, assigns work, makes final calls), Inventory (stock by SKU and size, shortfalls, which vendor can restock), Accounting (cash, invoices, margins, payments and purchase orders for human approval), Facilities (leases, rent, shop space), and Customer Service (drafts customer messages). Shop data is `data/campus_customs.db` (tables: desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, invoices). Tools update a working copy, `data/campus_customs_new.db`; the original stays untouched so tickets can be reset. Shop “today” is `desk.date_today`. Vendor lead times come from `vendors`. A vendor will not ship while they have an open unpaid invoice. Payments need human approval and must update the relevant table. The pay tool must refuse if cash is insufficient (no negative balances). Cash only goes out. Do not email customers or call real vendors; drafts stay on the board. AI calls use `PORTKEY_API_KEY` and only `gpt-6-luna` through Portkey.

For each problem, use this shape:

1. **Problem N — Title**
2. Prompt(s) I typed (in my own words), quoted
3. If follow-ups were needed: rationale for why, in one sentence (in my own words)

---

## Problem 1 — Vibe Coder Prompts

### Initial setup prompt

> I need a new Folder under AI - Call it Whetzel Homework 5

### Scenario prompt

> I'm going to send you pics of the scenario for our problem set and then We are going to walk through a handful of problems togetther like in simimlar homeowkrs

### Data prompt

> /Users/meredithwhetzel/Downloads/data-3

Scenario screenshots were attached with that data path (Campus Customs Multi-Agent Operations, the shop database, and the rules of the shop).

### Main Problem 1 prompt

> Okay Problem 1 - Vibe Coder Prompts. Create AI_prompts.md at the start of this and keep it updated as we work. The file is the log of what I type to you my vibe coder. Put one section for each problem. Each section must include the problem number and title, and the prompts I use - the first as well as follow ups and rationale in one sentence as to why the follow up was needed. Please do this and confirm we've done problem 1 successfully and correctly.

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*

---

## Problem 2 — Study the Campus Customs Database

### Main Problem 2 prompt

> Great now let's move on to Problem 2 - Study the Campus Customs Database. We need to open data/campus_customs.db and look through every table and ist field. Copy the original file to data/campus_customs_new.db. Later problems well need to update that working copy. Tell me about and study the three open tickets and describe to me how they link to other tables. Also, start output/harness.md. For each table, list the fields and one short line on why that table matters for the agents. We're going to need to keep growing this harness file in later problems. Tell me all I need to know to get what we're doing, and then confirm we've done problem 2 corrrectly

### Follow-up — second check

> A follow up because I'm less confident - are you sure we've done this correclty

**Why follow-ups were needed (my words):**  
I'm less confident, so I needed a second check that Problem 2 was done correctly.

---

## Problem 3 — Build the MCP Server

### Main Problem 3 prompt

> Okay let's move on to Problem 3 - Build the MCP Server. Write an MCP servier in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. We don't need to connect or run it in this program. We'll have every agent in this homework use the tools in this MCP server. We will add more tools to it later but for now we want three tools that we will need for the tickets in the database. Can you please give me your three recommended tools with clear names. Then build them / make sure theyre set up for use - never invent any data, only use information in the database. In output/harness.md, list each of our three MCP tools. For every tool include which table it reads, which ticket it helps unlock (101, 102, or 103) and one sentence based on what you think as to why the tool is right for the ticket / why you recommended it. Vague lines like "reads inventory" will score low - we need to be naunced and tie the tool to the ticket. Also add a short mcp_server/README.md file that explains what the MCP server is for, which database it uses, and the three tools it has. Then confirm all this has been done correctly and that we can move on to Problem 4 in a way that would make Tauhid proud!

### Follow-up — was it finished

> is problem 3 done?

### Follow-up — confirm again

> Okay so just to confirm question 3 is done

**Why follow-ups were needed (my words):**  
I just wanted to confirm question 3 is done.

---

## Problem 4 — Add the MCP Server to Vibe Coder and Test Each Tool

### Main Problem 4 prompt

> Okay now Problem 4 - Add the MCP Server to Vibe Coder and Test Each Tool. We need to add my MCP server to this project so that you, the vibe coder, can call the tools. Save the connection JSON text in .mcp.json at the project root (or however you, the vibe coder, saves local MCP server lists). Once you, the vibe coder, are connected, test each of the three MCP tools. Save evidence in output/mcp_smoke.json. For every tool include the prompt I asked the vibe coder (which may apply to multiple tools), the tool name, and the tool output (must match values in data/campus_customs_new.db. Once you do this, pressure test probelm 4 is done accurately and well to Tauhid's liking and let me know if we can move on to problem 5

### Follow-up — was it finished

> Is problem 4 done?

### Follow-up — how to fix it

> How do i fix this

**Why follow-ups were needed (my words):**  
*(fill in if / when I revise — agent must not invent this)*

---

## Problem 5 — Build the Agent Team and Grow the MCP Tools

### Main Problem 5 prompt

> Okay Problem 5 - Build the Agent Team and Grow the MCP Tools. Build the agent team for Campus Customs using PydanticAI: Boss, Inventory, Accounting, Faciilties, and CUstomer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. put the agent prompts in backend/prompts/ - one file per agent. Put data types in backend/models.py, and the agent files under backend/ (layout can vary as long as the five roles are clear). Use my portkey_api_key and only gpt-6-luna for every agent. We will also need to write a prompt with the shop rules the agent needs, more detailed prompts that cover all aspects of an agents work and scope score higher than a short generic one. What would you suggest, why, and then assume we do that. Add any tools the agents need to our MCP server so that they can work on the open tickets. Shop facts come from the MCP server over data/campus_custooms_new.db - do not invest a second shop tools layer that bypasses MCP. Wire the agents so they append to output/audit_trail.json as they rul: for each agent loop step, recorrd enough to audit later. Append to this file, do not wipe it each run. In output/harness.md, list each agent and each MCP tool (including ones we add in this problem) along with which table the tool uses. Also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check. Update mcp_server/README.md. Confirm we've done all of this right because its a big question. and then once youve pressure tested it let me know if were ready to move on to problem 6

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*

---

## Problem 6 — Plan The Three Tickets

### Main Problem 6 prompt

> Okay Problem 6 - Plan The Three Tickets. Before we wire the backend, we need to write down what we expect the team to do on each open ticket. Build output/desk_tickets.html - a page you can double click with one tab per ticket (101, 102, and 103). Also add empty cash and reflection tabs for later problems (leave them black for now). On each ticket tab, fill an Expected section only (leave room for an Actual section that we fill after we run the agents). For each ticket's Expected section, write in down your recommendations as to who the boss should call first and why, all the agent delegations we'd expect - not "boss calls everyon", which mcp tools you expect that run to use. Plans thatt send every specialist on every ticket score low. Tauhid will plan to compare to what actually happens when your agents resolve the three tickets. So, we need to be creative. Do this then let me know when you have pressure tested problem 6 and we can move on to problem 7

### Follow-up — second check

> Are we sure probelm 6 is done

**Why follow-ups were needed (my words):**  
I wanted to be sure problem 6 is done.

---

## Problem 7 — Backend Routes

### Main Problem 7 prompt

> Problem 7 - Backend Routes. Our React frontend dashboard (the next problem) needs a backend it can call. In backend/main.py, use FastAPI and add routes that do the following: return the three tickets and whether each is open or resolved, take a ticket id and run the agent team on that ticket, return recent agent events - what each agent said and which tools they used - so the board can refresh, approve a payment or purchase after a human clicks approve (agent only prepare the pay; this route is what actually changes cash), return the current checking balance from cash_accounts, reset the database to the original values when you want to try a fresh run. From the backend/ folder, start the server with uvicorn main:app --reload --port 8000. This turns on our backend at http://locahost:8000 so the frontend dashboard can call those routes. In output/harness.md, list each route in one line (what URL / what it does). Please pressure test probelm 7 and confirm when ready to move to problem 8

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*

---

## Problem 8 — Agent Dashboard

### Main Problem 8 prompt

> Problem 8 - Agent Dashboard. Build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes we build in Problem 7. At minimum, the board should: list all three tickets, let you pick one ticket and start the agent team on it, show each agent and what they are saying / doing while the ticket runs, mark a ticket resolved when the run finishes, show a short summary of what each agent did on that ticket, let a human approve a pay or purchase when asked, show the checking balance (it should drop after an approved pay). Make the dashboard look good. Let's be creative - make it girl boss-ey. This is a real desk people would want to sit at, so put thought into how it looks. Leverage what you know. Tell the front end to talk to the backend at http://localhost:8000. On tthe backend, allow the Vite page original (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with npm run dev. this opens the React desk in our browswer so we can pick tickets and watch agents. Write output/design.md with what you chose for the dashboard look (girly, layout, how agents read differently, how resolved tickets and cash show up) and why - including the creative choices that make it feel special and something humans would actually enjoy using. Do some research on this so that our design and our answers to this look good. Pressure test this is done from top to bottom on Problem 8 and that we can move on to Problem 9

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*

---

## Problem 9 — Resolve the Tickets

### Main Problem 9 prompt

> Problem 9 - Resolve the Tickets. Before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.bd again so we start clean. Note that starting checking balance. Then run all three tickets on the board (101, 102, 103) until each is resolved. Open output/desk_ticket.html from Problem 6. On each ticket tab, fill the Actual section from the run: which agents worked, what they delegaed, and which tools they used. Keep our Expected section so we can compare the two. On the Cash tab of the same output/desk_ticket.html, itemize the money: starting checking balance (after the reset), for each ticket - how cash changed when the ticket resolved and why (which pay / purchase, dollar amount), ending checking balance - it must match cash_accounts in the working database. Then, remember that wrong cash math loses points even if the board shows every ticket resolved. Also save: 1. output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals, 2. output/resolved_board.html - a page you can double click, with a screenshot of your React board for each resolved ticket (101, 102, and 103). Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the give agents, api routes, the dashboard, and the safety rules. Pressure test all of this and then let me know when were ready to move onto Problem 10.

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*

---

## Problem 10 — Reflection

### Main Problem 10 prompt

> Problem 10 - Reflection. Open output/desk_tickets.html and fill in the Reflection tab. We need to answer in our own girl boss vibe, and we need to be detailed and thorough. A little bit Scottie from Suits, a little bit Christina Yang from Greys anatomy. Here's the questions: How would you evlauate the performance of the agents one ach ticket and why? For each ticket, how did Actual compare to the expected plan you wrote earlier? What would have been simpler as one agent with tools and why? Describe three new problems Campus Customs might face that this agent team could solve with the tools we built. Describe three new problems Campus Customs might face that this agent team could not solve with the tools we built, and explain the tools and agents we would need to solve them. Tie every answer to this app and the three tickets we ran - use the ticket tabs and cash tab on the same page as our evidence. Generic AI essays without campus customs details will score low so be nuanced, and try to differentiate amongst a class of 77 other students. Let me know when we've done this all and pressure tested and give me rationale for your answers. Then, once youre sure, we can move on to problm 11.

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*

---

## Problem 11 — Submit to GitHub

### Main Problem 11 prompt

> Problem 11 - Submit to GitHub. Push our code to a public GitHub repository so graders can clone it. I'll submit the repo URL to canvas, and also put it in the output/github_url.txt. Do not push our real .env to GitHub repo. Do include both database files under data/ (the original and our working copy) so graders can run our app easily. I added some photos of the expected file layout. README should explain: copy original DB to the working copy when we need a clean run, start MCP server, start FastAPI backend, start the React baord, reset the DB before a full three-ticket run.

**Why follow-ups were needed (my words):**  
*(none yet — fill in if / when I revise — agent must not invent this)*
