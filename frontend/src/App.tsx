import { useEffect, useMemo, useState } from "react";
import { approveTicket, getCash, getEvents, getTickets, resetBook, runTicket } from "./api";
import type { AgentEvent, AgentTurn, Cash, Ticket } from "./types";

const ROLES = [
  { id: "boss", name: "Boss", line: "Makes the call" },
  { id: "inventory", name: "Inventory", line: "The shelf" },
  { id: "accounting", name: "Accounting", line: "The book" },
  { id: "facilities", name: "Facilities", line: "The lease" },
  { id: "customer_service", name: "Customer Service", line: "The note" },
] as const;

function money(value: number | null): string {
  if (value == null) return "—";
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function latestFor(role: string, events: AgentEvent[]): { said: AgentEvent | undefined; tool: string | null } {
  const mine = events.filter((event) => event.agent === role);
  const said = [...mine].reverse().find((event) => event.said);
  const tool = [...mine].reverse().find((event) => event.tool && event.tool !== "final_result");
  return { said, tool: tool?.tool ?? null };
}

function saidText(event: AgentEvent | undefined): string {
  if (!event) return "";
  const raw = event.said || "";
  if (raw.startsWith("{") || raw.startsWith("[")) {
    try {
      const parsed = JSON.parse(raw) as { summary?: string; result?: { summary?: string } };
      return parsed.summary || parsed.result?.summary || raw.slice(0, 220);
    } catch {
      return raw.slice(0, 220);
    }
  }
  return raw;
}

export function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [shopToday, setShopToday] = useState<string | null>(null);
  const [cash, setCash] = useState<Cash | null>(null);
  const [previousCash, setPreviousCash] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number>(101);
  const [running, setRunning] = useState(false);
  const [live, setLive] = useState<AgentEvent[]>([]);
  const [result, setResult] = useState<AgentTurn | null>(null);
  const [approver, setApprover] = useState("");
  const [paying, setPaying] = useState(false);
  const [paidNote, setPaidNote] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const [board, drawer] = await Promise.all([getTickets(), getCash()]);
    setTickets(board.tickets);
    setShopToday(board.shop_today);
    setCash(drawer);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? null;
  const dropped = previousCash != null && cash?.balance != null && cash.balance < previousCash;

  const summaries = useMemo(() => {
    return ROLES.map((role) => {
      const latest = latestFor(role.id, live);
      return { ...role, tool: latest.tool, text: saidText(latest.said), spoke: Boolean(latest.said || latest.tool) };
    });
  }, [live]);

  async function onRun() {
    if (!selected) return;
    setError("");
    setPaidNote("");
    setResult(null);
    setLive([]);
    setRunning(true);
    const before = await getEvents();
    const knownRuns = new Set(before.events.map((event) => event.run_id));
    const timer = window.setInterval(async () => {
      try {
        const data = await getEvents();
        setLive(data.events.filter((event) => !knownRuns.has(event.run_id)));
      } catch {
        /* The run is still going. The next poll can recover. */
      }
    }, 1000);
    try {
      const data = await runTicket(selected.id);
      setResult(data.result);
      setLive(data.events);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The run stopped.");
    } finally {
      window.clearInterval(timer);
      setRunning(false);
    }
  }

  async function onApprove() {
    if (!selected) return;
    const name = approver.trim();
    if (name.length < 2) {
      setError("Sign the check with your name.");
      return;
    }
    setPaying(true);
    setError("");
    setPreviousCash(cash?.balance ?? null);
    try {
      const payment = await approveTicket(selected.id, name);
      setPaidNote(
        payment.paid
          ? `Signed. ${money(payment.amount ?? null)} went out.`
          : payment.reason || "The book did not take the payment.",
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval did not go through.");
    } finally {
      setPaying(false);
    }
  }

  async function onReset() {
    setError("");
    setResult(null);
    setLive([]);
    setPaidNote("");
    setPreviousCash(null);
    try {
      await resetBook();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    }
  }

  return (
    <main className="desk">
      <header className="masthead">
        <div>
          <p className="eyebrow">Campus Customs</p>
          <h1>The night desk</h1>
          <p className="today">Shop today {shopToday ?? "—"}</p>
        </div>
        <div className={`drawer ${dropped ? "dropped" : ""}`}>
          <p className="eyebrow">Checking</p>
          <p className="balance">{money(cash?.balance ?? null)}</p>
          <p className="asof">{cash?.date ? `as of ${cash.date}` : "balance loading"}</p>
        </div>
      </header>

      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}

      <section className="board" aria-label="Open tickets">
        {tickets.map((ticket) => (
          <button
            key={ticket.id}
            type="button"
            className={`ticket ${ticket.id === selectedId ? "selected" : ""} ${ticket.state}`}
            onClick={() => {
              setSelectedId(ticket.id);
              setResult(null);
              setLive([]);
              setPaidNote("");
              setError("");
            }}
          >
            <span className="ticket-id">{ticket.id}</span>
            <span className="ticket-subject">{ticket.subject}</span>
            <span className="ticket-who">{ticket.requester}</span>
            {ticket.state === "resolved" ? <span className="stamp">Handled</span> : <span className="state">Open</span>}
          </button>
        ))}
      </section>

      <section className="work" aria-label="Selected ticket">
        {selected ? (
          <>
            <div>
              <p className="eyebrow">{selected.type.replaceAll("_", " ")}</p>
              <h2>{selected.subject}</h2>
              <p className="note">{selected.notes}</p>
              <p className="meta">
                {selected.sku ? `${selected.sku} · size ${selected.size ?? "—"} · qty ${selected.qty ?? "—"}` : "No merchandise on this ticket"}
              </p>
            </div>
            <div className="actions">
              <button type="button" className="run" onClick={onRun} disabled={running}>
                {running ? "The desk is working…" : "Send it to the team"}
              </button>
              <button type="button" className="quiet" onClick={onReset} disabled={running}>
                Reset the book
              </button>
            </div>
          </>
        ) : (
          <p>The board is empty.</p>
        )}
      </section>

      <section className="staff" aria-label="Agent team">
        {summaries.map((role) => (
          <article key={role.id} className={`plate plate-${role.id} ${role.spoke ? "speaking" : ""}`}>
            <header>
              <h3>{role.name}</h3>
              <p>{role.line}</p>
            </header>
            <p className="speech">
              {running && !role.text
                ? "At her desk."
                : role.text || (result ? "She sat this one out." : "Waiting for a ticket.")}
            </p>
            {role.tool ? <p className="tool">{role.tool}</p> : null}
          </article>
        ))}
      </section>

      {result ? (
        <section className="summary" aria-label="Run summary">
          <h2>What they decided</h2>
          <p>{result.summary}</p>
          <p className="recommendation">{result.recommendation}</p>
          {result.needs_human_approval ? (
            <form
              className="approve"
              onSubmit={(event) => {
                event.preventDefault();
                void onApprove();
              }}
            >
              <label htmlFor="approver">Sign the check</label>
              <input
                id="approver"
                value={approver}
                onChange={(event) => setApprover(event.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
              <button type="submit" disabled={paying}>
                {paying ? "Signing…" : "Approve the payment"}
              </button>
            </form>
          ) : null}
          {paidNote ? <p className="paid">{paidNote}</p> : null}
        </section>
      ) : null}
    </main>
  );
}
