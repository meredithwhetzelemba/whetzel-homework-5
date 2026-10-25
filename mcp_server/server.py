"""Campus Customs MCP server.

Agents call these tools over MCP. This file does not start the server on
import. Run it later with: python server.py
from this directory. Shop data is data/campus_customs_new.db.
"""

from __future__ import annotations

from fastmcp import FastMCP

from tools import (
    get_checking_balance,
    list_board_tickets,
    list_open_tickets,
    lookup_bulk_discount_margin,
    lookup_order_stock_and_reprint_invoice,
    lookup_rent_due_against_cash,
    pay_approved_obligation,
    resolve_ticket,
    save_board_draft,
)

mcp = FastMCP("Campus Customs Operations")
mcp.tool()(list_board_tickets)
mcp.tool()(get_checking_balance)
mcp.tool()(list_open_tickets)
mcp.tool()(lookup_order_stock_and_reprint_invoice)
mcp.tool()(lookup_rent_due_against_cash)
mcp.tool()(lookup_bulk_discount_margin)
mcp.tool()(save_board_draft)
mcp.tool()(pay_approved_obligation)
mcp.tool()(resolve_ticket)


if __name__ == "__main__":
    # stdio must stay clean JSON-RPC. The banner would write on top of it.
    mcp.run(transport="stdio", show_banner=False)
