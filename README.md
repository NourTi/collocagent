# CollocAgent

[![tests](https://github.com/NourTi/collocagent/actions/workflows/tests.yml/badge.svg)](https://github.com/NourTi/collocagent/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CollocAgent is a **standalone, local application** for conservative collocation feedback in academic English. It runs entirely on the local machine and requires no external service, hosted platform, or commercial model API. The artifact exposes the same pipeline through:

- a browser interface (`http://127.0.0.1:8000`),
- a JSON endpoint (`POST /api/analyze`), and
- a command-line interface (`python -m collocagent ...`).

## Important research-integrity boundary

The bundled `data/demo_corpus.txt` is **synthetic** and exists only to prove that the software runs. It must not be described as COCA, BNC, or empirical research data. For a paper-level experiment, build an index from a corpus you are licensed to use and document that corpus in the manuscript.

## Quick start

```bash
cd collocagent
python -m collocagent build-demo
python -m collocagent analyze "The researchers make an experiment." --pretty
python -m collocagent.server
```

Open `http://127.0.0.1:8000` in a browser.

## Build an index from your own corpus

Place one or more UTF-8 `.txt` files in a folder, then run:

```bash
python -m collocagent build-index corpus/*.txt \
  --name "My licensed academic corpus" \
  --index data/my_corpus.sqlite3

python -m collocagent analyze "Your text here" \
  --index data/my_corpus.sqlite3 --pretty
```

Each result records the corpus name, SHA-256 fingerprint, window size, counts, association scores, and retrieved concordance lines. If evidence is absent, the agent returns `insufficient_corpus_evidence` rather than inventing a frequency.

## API example

```bash
curl -s http://127.0.0.1:8000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"This finding has big importance."}'
```

## Tests

```bash
python -m collocagent build-demo
python -W error::ResourceWarning -m unittest discover -s tests -v
PYTHONPATH=. python scripts/evaluate_smoke.py
```

The corpus index is generated, not version-controlled, so `build-demo` must run
once in a fresh checkout before the smoke evaluation. Continuous integration
runs these commands on Python 3.10 and 3.13, the oldest and newest supported
versions, on every push.

The included smoke fixtures verify routing and output contracts only. They are not an external benchmark and are not evidence of model effectiveness.

## Docker

```bash
docker compose up --build
```

## Public deployment

`render.yaml` is a Render blueprint that deploys this repository unchanged, from
the repository `Dockerfile`, on a free instance. The service reads the port to
bind from `PORT` and answers a health check on `/health`. Any host that can run
a container will serve the artifact the same way; nothing in the system depends
on a particular provider.

## Repository contents

- `collocagent/`: pipeline, indexer, CLI, and local HTTP service
- `web/`: browser interface
- `data/rules.json`: auditable diagnostic rules and candidate inventory
- `data/demo_corpus.txt`: synthetic software fixture
- `tests/`: unit tests
- `scripts/evaluate_smoke.py`: constructed engineering smoke test
- `artifacts/`: recorded verification outputs

## License

MIT for the software. Corpus files retain their original licences and must not be redistributed unless permission allows it.
