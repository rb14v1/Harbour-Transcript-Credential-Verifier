from django.test import TestCase

from apps.common import search_store


class SearchStoreStubTests(TestCase):
    def setUp(self):
        self.index_name = "unit-test-index"
        search_store.clear_index(self.index_name)

    def tearDown(self):
        search_store.clear_index(self.index_name)

    def test_upsert_and_search_returns_closest_match_first(self):
        items = [
            {"id": "a", "vector": [1.0, 0.0, 0.0], "payload": {"label": "a"}},
            {"id": "b", "vector": [0.0, 1.0, 0.0], "payload": {"label": "b"}},
            {"id": "c", "vector": [0.9, 0.1, 0.0], "payload": {"label": "c"}},
        ]
        count = search_store.upsert_chunks(self.index_name, items)
        self.assertEqual(count, 3)

        results = search_store.search(self.index_name, [1.0, 0.0, 0.0], top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["payload"]["label"], "a")
        self.assertEqual(results[1]["payload"]["label"], "c")

    def test_search_on_empty_index_returns_empty_list(self):
        results = search_store.search("never-upserted-index", [1.0, 0.0], top_k=5)
        self.assertEqual(results, [])

    def test_upsert_overwrites_same_id(self):
        search_store.upsert_chunks(self.index_name, [{"id": "x", "vector": [1, 0], "payload": {"v": 1}}])
        search_store.upsert_chunks(self.index_name, [{"id": "x", "vector": [1, 0], "payload": {"v": 2}}])
        self.assertEqual(search_store.index_size(self.index_name), 1)
