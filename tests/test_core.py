from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from collocagent.agents import CollocAgent
from collocagent.corpus import CorpusIndex, tokenize

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules.json"
DEMO = ROOT / "data" / "demo_corpus.txt"


class CorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.index_path = Path(self.temp.name) / "test.sqlite3"
        self.index = CorpusIndex(self.index_path)
        self.meta = self.index.build(
            [DEMO], corpus_name="test synthetic corpus", window=4
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_tokenize(self) -> None:
        self.assertEqual(tokenize("Researchers' evidence."), ["researchers", "evidence"])

    def test_fingerprint_present(self) -> None:
        self.assertEqual(len(self.meta["fingerprint_sha256"]), 64)

    def test_association_is_computed(self) -> None:
        stats = self.index.association("conduct", "experiment")
        self.assertGreater(stats["pair_count"], 0)
        self.assertIsNotNone(stats["log_dice"])

    def test_concordance_is_retrieved(self) -> None:
        lines = self.index.concordances("conduct", "experiment")
        self.assertTrue(any("experiment" in line.lower() for line in lines))


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.index_path = Path(cls.temp.name) / "test.sqlite3"
        CorpusIndex(cls.index_path).build(
            [DEMO], corpus_name="test synthetic corpus", window=4
        )
        cls.agent = CollocAgent(RULES, cls.index_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_known_error_is_detected(self) -> None:
        result = self.agent.analyze("We make an experiment to test the claim.")
        self.assertEqual(result["issue_count"], 1)
        self.assertEqual(result["issues"][0]["recommended"], "conduct an experiment")

    def test_clean_sentence_is_not_overcorrected(self) -> None:
        result = self.agent.analyze("We conducted an experiment to test the claim.")
        self.assertEqual(result["issue_count"], 0)

    def test_evidence_has_provenance(self) -> None:
        issue = self.agent.analyze("This has big importance.")["issues"][0]
        self.assertEqual(issue["evidence_status"], "attested_in_indexed_corpus")
        self.assertEqual(len(issue["corpus"]["fingerprint_sha256"]), 64)

    def test_empty_text_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.agent.analyze("   ")

    def test_rules_are_valid_json(self) -> None:
        rules = json.loads(RULES.read_text())
        self.assertGreaterEqual(len(rules), 10)


if __name__ == "__main__":
    unittest.main()
