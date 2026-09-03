"""Serverless entrypoint that publishes the CollocAgent demo on Vercel.

The Vercel Python runtime loads the top-level name ``handler`` and calls it as a
``http.server.BaseHTTPRequestHandler`` subclass.  The released artifact already
exposes that exact class, so this module deploys the published request handlers
unchanged and only adapts the hosting environment:

* the platform filesystem is read-only apart from ``/tmp``, so the generated
  corpus index is written there instead of next to the bundled corpus;
* a catch-all rewrite sends every path to this function, so the request path is
  normalised before the released handlers inspect it.

No analysis, scoring, or rule logic is defined here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Only /tmp is writable on the platform, so the index is generated there.
os.environ.setdefault("COLLOCAGENT_INDEX", "/tmp/collocagent.sqlite3")

from collocagent.agents import CollocAgent  # noqa: E402
from collocagent.server import INDEX, RULES, Handler, ensure_index  # noqa: E402

ensure_index()
Handler.agent = CollocAgent(RULES, INDEX)
