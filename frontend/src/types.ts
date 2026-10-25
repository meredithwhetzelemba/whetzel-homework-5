export type Ticket = {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  status: string;
  state: "open" | "resolved";
  notes: string | null;
};

export type Board = {
  shop_today: string | null;
  tickets: Ticket[];
};

export type Cash = {
  found: boolean;
  name: string;
  balance: number | null;
  date: string | null;
};

export type AgentEvent = {
  timestamp: string;
  run_id: string;
  agent: string;
  said: string;
  tool: string | null;
  stop_reason: string | null;
};

export type AgentTurn = {
  role: string;
  summary: string;
  ticket_ids: number[];
  facts_used: string[];
  recommendation: string;
  needs_human_approval: boolean;
  customer_draft: string | null;
  refused: boolean;
};

export type RunResponse = {
  ticket_id: number;
  result: AgentTurn;
  events: AgentEvent[];
  resolved: { resolved?: boolean; state?: string } | null;
};
