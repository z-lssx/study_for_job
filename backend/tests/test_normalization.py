from __future__ import annotations

import unittest
from uuid import uuid4

from app.intelligence.normalization.text import normalize_question_text, occurrence_key, question_normalization_key


class CanonicalQuestionTextTests(unittest.TestCase):
    def test_conservative_normalization_keeps_meaningful_punctuation(self):
        self.assertEqual("Redis 为什么快", normalize_question_text("Redis  为什么快？"))
        self.assertEqual(
            question_normalization_key("Redis 为什么快？"),
            question_normalization_key("redis  为什么快"),
        )
        self.assertNotEqual(
            question_normalization_key("C++ 的 RAII 是什么？"),
            question_normalization_key("C 的 RAII 是什么？"),
        )

    def test_occurrence_key_is_scoped_to_document_and_round(self):
        document_id = uuid4()
        key = question_normalization_key("Redis 为什么快")
        self.assertEqual(occurrence_key(document_id, 1, key), occurrence_key(document_id, 1, key))
        self.assertNotEqual(occurrence_key(document_id, 1, key), occurrence_key(document_id, 2, key))
        self.assertNotEqual(occurrence_key(document_id, 1, key), occurrence_key(uuid4(), 1, key))


if __name__ == "__main__":
    unittest.main()
