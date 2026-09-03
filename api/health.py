"""Serverless entrypoint that answers the released status check on Vercel.

The platform routes only ``/health`` to this function.  Because a catch-all
rewrite hands each function the rewrite *destination* rather than the address
the reader typed, the released status route is selected explicitly here instead
of being inferred from the incoming path.

The corpus index is deliberately not opened: the released status route reports
software identity only and never consults the corpus, so no analysis object is
required and nothing is written to disk.  No analysis, scoring, or rule logic is
defined here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Kept consistent with the analysis entrypoint: only /tmp is writable.
os.environ.setdefault("COLLOCAGENT_INDEX", "/tmp/collocagent.sqlite3")

from collocagent.server import Handler  # noqa: E402


class handler(Handler):  # noqa: N801 - name required by the Vercel runtime
    """Released handler pinned to the status route."""

    def do_GET(self) -> None:  # noqa: N802
        self.path = "/health"
        super().do_GET()
