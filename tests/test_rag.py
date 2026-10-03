import json
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from ai.rag import Passage, Hit, KnowledgeIndex, chunk_pages, read_documents
from ai.providers import AIError, chat


class Tokenizer:
    def __call__(self, text, **kwargs):
        matches = list(re.finditer(r"\S+", text))
        return {"input_ids": list(range(len(matches))), "offset_mapping": [m.span() for m in matches]}


class Encoder:
    def encode(self, texts, **kwargs):
        data = np.array([[1., 0., 0.] if "plaster" in t.lower() else [0., 1., 0.] for t in texts], dtype="float32")
        return data


class RAGTests(unittest.TestCase):
    def test_chunking_retains_casing_page_and_overlap(self):
        text = " ".join(f"Word{i}" for i in range(440))
        chunks = chunk_pages([("doc.txt", 7, text)], Tokenizer())
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[1].text.split()[0], "Word168")
        self.assertEqual(chunks[-1].page, 7)
        self.assertTrue(chunks[-1].text.endswith("Word439"))

    def test_actual_faiss_ranks_known_vectors(self):
        a, b = Passage("S0001", "a.txt", 1, "PLASTER"), Passage("S0002", "b.txt", 2, "steel")
        index = KnowledgeIndex([a, b], Encoder())
        hits = index.search("plaster", threshold=.8)
        self.assertEqual([h.passage.id for h in hits], ["S0001"])
        self.assertAlmostEqual(hits[0].score, 1.)

    def test_private_indexes_do_not_share_passages(self):
        first = KnowledgeIndex([Passage("S0001", "first.txt", 1, "plaster")], Encoder())
        second = KnowledgeIndex([Passage("S0001", "second.txt", 1, "steel")], Encoder())
        self.assertEqual(first.search("plaster")[0].passage.filename, "first.txt")
        self.assertEqual(second.search("steel")[0].passage.filename, "second.txt")

    def test_duplicate_documents_are_not_added_twice(self):
        pages, warnings = read_documents([("one.txt", b"Plaster thickness 15 mm."), ("two.txt", b"Plaster thickness 15 mm.")])
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(warnings), 1)

    def test_unsupported_file_and_empty_text_rejected(self):
        for files in [[("a.exe", b"abc")], [("a.txt", b" ")], [("a.txt", b"\xff")]]:
            with self.subTest(files=files), self.assertRaises(ValueError):
                read_documents(files)

    def response(self, result):
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(result)))])

    def test_no_evidence_abstains_without_api_call(self):
        with patch("groq.Groq") as client:
            result = chat("fake-key", "openai/gpt-oss-120b", "question", document_only=True)
            client.assert_not_called()
            self.assertFalse(result["sources"])

    def test_invented_citation_is_rejected(self):
        with patch("groq.Groq") as client:
            client.return_value.__enter__.return_value.chat.completions.create.return_value = self.response(dict(answer="Made up [S9999]", citations=["S9999"]))
            with self.assertRaises(AIError):
                chat("fake-key", "openai/gpt-oss-120b", "question", hits=[Hit(Passage("S0001", "x.txt", 1, "Evidence"), .7)], document_only=True)

    def test_uncited_document_answer_is_withheld(self):
        with patch("groq.Groq") as client:
            client.return_value.__enter__.return_value.chat.completions.create.return_value = self.response(dict(answer="The price is 5000.", citations=[]))
            result = chat("fake-key", "openai/gpt-oss-120b", "price?", hits=[Hit(Passage("S0001", "x.txt", 1, "No price listed"), .7)], document_only=True)
            self.assertNotIn("5000", result["answer"])


if __name__ == "__main__":
    unittest.main()
