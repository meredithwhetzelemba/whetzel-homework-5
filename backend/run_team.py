"""Run the Campus Customs team from the terminal.

Example, from the backend folder:
    python run_team.py "Review the open tickets. Do not pay and do not email."
"""

from __future__ import annotations

import asyncio
import sys

from audit import AUDIT_PATH
from team import run_boss


async def _main() -> None:
    task = " ".join(sys.argv[1:]).strip()
    if not task:
        task = "Review every open ticket. Delegate the work. Do not pay and do not email."
    answer = await run_boss(task)
    print(answer.model_dump_json(indent=2))
    print(f"\nAudit trail: {AUDIT_PATH}")


if __name__ == "__main__":
    asyncio.run(_main())
