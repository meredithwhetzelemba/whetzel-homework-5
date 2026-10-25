import type { Board, Cash, RunResponse } from "./types";

const API = "http://localhost:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (detail?.reason) return String(detail.reason);
    return JSON.stringify(detail ?? body);
  } catch {
    return response.statusText || "The desk could not reach the backend.";
  }
}

export async function getTickets(): Promise<Board> {
  const response = await fetch(`${API}/tickets`);
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function getCash(): Promise<Cash> {
  const response = await fetch(`${API}/cash`);
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function getEvents(): Promise<{ events: RunResponse["events"] }> {
  const response = await fetch(`${API}/events?limit=80`);
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function runTicket(ticketId: number): Promise<RunResponse> {
  const response = await fetch(`${API}/tickets/${ticketId}/run`, { method: "POST" });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function approveTicket(ticketId: number, approvedBy: string): Promise<{
  paid: boolean;
  amount?: number;
  checking_balance?: number;
  reason?: string;
}> {
  const response = await fetch(`${API}/tickets/${ticketId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved_by: approvedBy }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function resetBook(): Promise<void> {
  const response = await fetch(`${API}/reset`, { method: "POST" });
  if (!response.ok) throw new Error(await readError(response));
}
