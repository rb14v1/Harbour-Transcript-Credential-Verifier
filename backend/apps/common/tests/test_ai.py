from django.test import TestCase

from apps.common import ai


class AiStubTests(TestCase):
    def test_embedding_has_correct_dimensions(self):
        vector = ai.generate_embedding("Data Structures and Algorithms")
        self.assertEqual(len(vector), ai.EMBEDDING_DIMENSIONS)
        self.assertTrue(all(isinstance(v, float) for v in vector))

    def test_embedding_is_deterministic(self):
        v1 = ai.generate_embedding("same text")
        v2 = ai.generate_embedding("same text")
        self.assertEqual(v1, v2)

    def test_different_text_gives_different_embedding(self):
        v1 = ai.generate_embedding("course one")
        v2 = ai.generate_embedding("course two")
        self.assertNotEqual(v1, v2)

    def test_chat_completion_is_deterministic_stub_text(self):
        reply1 = ai.chat_completion("system", "user question")
        reply2 = ai.chat_completion("system", "user question")
        self.assertEqual(reply1, reply2)
        self.assertIn("stub-ai", reply1)

    def test_pad_vector_handles_small_dimensions(self):
        vector = ai.pad_vector(b"seed", dimensions=5)
        self.assertEqual(len(vector), 5)
