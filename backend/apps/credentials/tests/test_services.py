from django.core.files.base import ContentFile
from django.test import TestCase

from apps.applicants.models import Applicant
from apps.common import blob_store, search_store
from apps.credentials import services
from apps.credentials.models import Credential, CredentialChunk, CredentialRecord


class ProcessCredentialServiceTests(TestCase):
    def setUp(self):
        search_store.clear_index(services.SEARCH_INDEX_NAME)
        self.applicant = Applicant.objects.create(full_name="Pat Student", email="pat.student@example.com")
        raw = b"Data Structures|A|Fall 2021\nOperating Systems|B+|Spring 2022\n"
        blob_path = blob_store.upload_document(
            ContentFile(raw, name="transcript.txt"), container="credentials", blob_name="svc_test_transcript.txt"
        )
        self.credential = Credential.objects.create(
            applicant=self.applicant,
            institution="Test University",
            credential_type=Credential.CredentialType.TRANSCRIPT,
            blob_path=blob_path,
        )

    def test_process_credential_creates_records_and_chunks_and_indexes_them(self):
        services.process_credential(self.credential)
        self.credential.refresh_from_db()

        self.assertEqual(self.credential.status, Credential.Status.PROCESSED)
        self.assertEqual(CredentialRecord.objects.filter(credential=self.credential).count(), 2)
        chunks = list(CredentialChunk.objects.filter(credential=self.credential).order_by("chunk_index"))
        self.assertEqual(len(chunks), 2)
        self.assertIn("Data Structures", chunks[0].chunk_text)

        self.assertEqual(search_store.index_size(services.SEARCH_INDEX_NAME), 2)

    def test_reprocessing_is_idempotent_and_replaces_rows(self):
        services.process_credential(self.credential)
        first_chunk_count = CredentialChunk.objects.filter(credential=self.credential).count()

        services.process_credential(self.credential)
        second_chunk_count = CredentialChunk.objects.filter(credential=self.credential).count()

        self.assertEqual(first_chunk_count, second_chunk_count)


class AnswerEquivalencyQuestionServiceTests(TestCase):
    def setUp(self):
        search_store.clear_index(services.SEARCH_INDEX_NAME)
        applicant = Applicant.objects.create(full_name="Pat Student", email="pat2.student@example.com")
        raw = b"Data Structures and Algorithms|A|Fall 2021\n"
        blob_path = blob_store.upload_document(
            ContentFile(raw, name="t.txt"), container="credentials", blob_name="svc_test_eq.txt"
        )
        self.credential = Credential.objects.create(
            applicant=applicant,
            institution="Test University",
            credential_type=Credential.CredentialType.TRANSCRIPT,
            blob_path=blob_path,
        )
        services.process_credential(self.credential)

    def test_answer_question_returns_text_and_cites_chunks(self):
        answer_text, chunk_ids = services.answer_equivalency_question(
            "Does this cover data structures equivalent to CS301?", credential=self.credential
        )
        self.assertTrue(answer_text)
        self.assertEqual(len(chunk_ids), 1)

    def test_ensure_index_populated_self_heals_empty_index(self):
        search_store.clear_index(services.SEARCH_INDEX_NAME)
        self.assertEqual(search_store.index_size(services.SEARCH_INDEX_NAME), 0)

        services.ensure_index_populated()

        # Rebuilds from every CredentialChunk row in the DB (this test's one
        # chunk, plus any pre-existing seed-data chunks).
        expected_total = CredentialChunk.objects.count()
        self.assertEqual(search_store.index_size(services.SEARCH_INDEX_NAME), expected_total)
