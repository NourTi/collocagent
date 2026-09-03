"""Corpus indexing and auditable association statistics for CollocAgent."""
from __future__ import annotations

import hashlib
import math
import re
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.split(text.strip()) if s.strip()]


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a.lower(), b.lower())))


class CorpusIndex:
    """SQLite index built from user-supplied plain-text corpora.

    The index stores token counts, unordered within-window pair counts, sentence
    concordances, and a SHA-256 fingerprint. It never labels generated examples
    as corpus evidence.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def build(
        self,
        text_paths: Iterable[str | Path],
        *,
        corpus_name: str,
        window: int = 4,
        replace: bool = True,
    ) -> dict:
        paths = [Path(p) for p in text_paths]
        if not paths:
            raise ValueError("At least one corpus text file is required")
        if window < 1:
            raise ValueError("window must be at least 1")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if replace and self.db_path.exists():
            self.db_path.unlink()

        unigram: Counter[str] = Counter()
        pairs: Counter[tuple[str, str]] = Counter()
        sentences: list[str] = []
        digest = hashlib.sha256()

        for path in sorted(paths, key=lambda p: str(p)):
            raw = path.read_bytes()
            digest.update(str(path.name).encode("utf-8"))
            digest.update(b"\0")
            digest.update(raw)
            text = raw.decode("utf-8", errors="replace")
            for sentence in split_sentences(text):
                tokens = tokenize(sentence)
                if not tokens:
                    continue
                sentences.append(sentence)
                unigram.update(tokens)
                for i, token in enumerate(tokens):
                    upper = min(len(tokens), i + window + 1)
                    for other in tokens[i + 1 : upper]:
                        if token != other:
                            pairs[pair_key(token, other)] += 1

        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE unigram (token TEXT PRIMARY KEY, count INTEGER NOT NULL);
                CREATE TABLE pair_count (
                    token_a TEXT NOT NULL,
                    token_b TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY (token_a, token_b)
                );
                CREATE TABLE sentence (id INTEGER PRIMARY KEY, text TEXT NOT NULL);
                """
            )
            meta = {
                "corpus_name": corpus_name,
                "fingerprint_sha256": digest.hexdigest(),
                "window": str(window),
                "total_tokens": str(sum(unigram.values())),
                "sentence_count": str(len(sentences)),
                "source_file_count": str(len(paths)),
            }
            conn.executemany("INSERT INTO meta(key,value) VALUES (?,?)", meta.items())
            conn.executemany(
                "INSERT INTO unigram(token,count) VALUES (?,?)", unigram.items()
            )
            conn.executemany(
                "INSERT INTO pair_count(token_a,token_b,count) VALUES (?,?,?)",
                ((a, b, c) for (a, b), c in pairs.items()),
            )
            conn.executemany(
                "INSERT INTO sentence(text) VALUES (?)", ((s,) for s in sentences)
            )
        return self.metadata()

    def metadata(self) -> dict:
        if not self.db_path.exists():
            return {"status": "missing", "db_path": str(self.db_path)}
        with closing(sqlite3.connect(self.db_path)) as conn:
            rows = conn.execute("SELECT key,value FROM meta").fetchall()
        data = dict(rows)
        for key in ("window", "total_tokens", "sentence_count", "source_file_count"):
            if key in data:
                data[key] = int(data[key])
        data["status"] = "ready"
        data["db_path"] = str(self.db_path)
        return data

    def association(self, first: str, second: str) -> dict:
        a, b = pair_key(first, second)
        with closing(sqlite3.connect(self.db_path)) as conn:
            f_first_row = conn.execute(
                "SELECT count FROM unigram WHERE token=?", (first.lower(),)
            ).fetchone()
            f_second_row = conn.execute(
                "SELECT count FROM unigram WHERE token=?", (second.lower(),)
            ).fetchone()
            f_pair_row = conn.execute(
                "SELECT count FROM pair_count WHERE token_a=? AND token_b=?", (a, b)
            ).fetchone()
            total = int(
                conn.execute("SELECT value FROM meta WHERE key='total_tokens'").fetchone()[0]
            )
        f_first = int(f_first_row[0]) if f_first_row else 0
        f_second = int(f_second_row[0]) if f_second_row else 0
        f_pair = int(f_pair_row[0]) if f_pair_row else 0
        log_dice = None
        pmi = None
        if f_pair > 0 and (f_first + f_second) > 0:
            log_dice = 14.0 + math.log2((2.0 * f_pair) / (f_first + f_second))
        if f_pair > 0 and f_first > 0 and f_second > 0 and total > 0:
            pmi = math.log2((f_pair * total) / (f_first * f_second))
        return {
            "first": first.lower(),
            "second": second.lower(),
            "pair_count": f_pair,
            "first_count": f_first,
            "second_count": f_second,
            "log_dice": round(log_dice, 4) if log_dice is not None else None,
            "pmi": round(pmi, 4) if pmi is not None else None,
            "total_tokens": total,
        }

    def concordances(self, first: str, second: str, limit: int = 3) -> list[str]:
        first_rx = re.compile(rf"\b{re.escape(first)}\b", re.IGNORECASE)
        second_rx = re.compile(rf"\b{re.escape(second)}\b", re.IGNORECASE)
        found: list[str] = []
        with closing(sqlite3.connect(self.db_path)) as conn:
            for (text,) in conn.execute("SELECT text FROM sentence ORDER BY id"):
                if first_rx.search(text) and second_rx.search(text):
                    found.append(text)
                    if len(found) >= limit:
                        break
        return found
