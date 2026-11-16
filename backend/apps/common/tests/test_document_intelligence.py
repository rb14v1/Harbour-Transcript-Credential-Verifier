from django.test import TestCase

from apps.common import document_intelligence


class DocumentIntelligenceStubTests(TestCase):
    def test_extracts_structured_rows_from_pipe_delimited_lines(self):
        raw = b"Data Structures|A|Fall 2021\nOperating Systems|B+|Spring 2022\n"
        records = document_intelligence.extract_records(raw, filename="transcript.txt")

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], {
            "course_or_subject": "Data Structures",
            "grade_or_score": "A",
            "term": "Fall 2021",
        })
        self.assertEqual(records[1]["course_or_subject"], "Operating Systems")

    def test_unparseable_line_still_produces_deterministic_record(self):
        raw = b"Just a plain course name with no delimiters"
        records_a = document_intelligence.extract_records(raw, filename="a.txt")
        records_b = document_intelligence.extract_records(raw, filename="a.txt")

        self.assertEqual(len(records_a), 1)
        self.assertEqual(records_a, records_b)  # deterministic / reproducible
        self.assertIn(records_a[0]["grade_or_score"], document_intelligence._GRADES)
        self.assertIn(records_a[0]["term"], document_intelligence._TERMS)

    def test_empty_document_still_returns_one_record(self):
        records = document_intelligence.extract_records(b"", filename="empty.txt")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["course_or_subject"], "General Studies")
