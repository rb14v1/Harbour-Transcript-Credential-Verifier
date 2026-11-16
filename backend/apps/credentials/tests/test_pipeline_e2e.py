"""
True end-to-end test of the full workflow, entirely through stub mode and
real HTTP API calls: upload -> extract -> chunk/embed -> index -> search ->
AI summary, with nothing mocked out - every "external" call goes through the
real apps/common stub implementations.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applicants.models import Applicant
from apps.common import search_store
from apps.credentials import services
from apps.credentials.models import CredentialChunk, CredentialRecord

User = get_user_model()


class FullPipelineEndToEndTests(APITestCase):
    def setUp(self):
        search_store.clear_index(services.SEARCH_INDEX_NAME)
        self.reviewer = User.objects.create_user(
            email="e2e.reviewer@example.com", password="Pass1234!", role=User.Role.ADMISSIONS_REVIEWER
        )
        resp = self.client.post("/api/auth/login/", {"email": self.reviewer.email, "password": "Pass1234!"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

        self.applicant = Applicant.objects.create(full_name="Morgan Scholar", email="morgan.scholar@example.com")

    def test_full_upload_to_answer_pipeline(self):
        # 1. Upload a transcript document for an applicant.
        upload = SimpleUploadedFile(
            "transcript.txt",
            (
                b"Data Structures and Algorithms|A|Fall 2021\n"
                b"Computer Networks|B+|Spring 2022\n"
                b"Theory of Computation|A-|Fall 2022\n"
            ),
            content_type="text/plain",
        )
        create_resp = self.client.post("/api/credentials/", {
            "applicant": self.applicant.id,
            "institution": "Summit University",
            "credential_type": "transcript",
            "file": upload,
        }, format="multipart")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED, create_resp.data)
        credential_id = create_resp.data["id"]
        self.assertEqual(create_resp.data["status"], "uploaded")

        # 2. Process: extract -> chunk/embed -> index.
        process_resp = self.client.post(f"/api/credentials/{credential_id}/process/")
        self.assertEqual(process_resp.status_code, status.HTTP_200_OK, process_resp.data)
        self.assertEqual(process_resp.data["status"], "processed")

        self.assertEqual(CredentialRecord.objects.filter(credential_id=credential_id).count(), 3)
        chunks = list(CredentialChunk.objects.filter(credential_id=credential_id))
        self.assertEqual(len(chunks), 3)
        self.assertEqual(search_store.index_size(services.SEARCH_INDEX_NAME), 3)

        # 3. Ask an equivalency question -> embeds -> searches -> summarizes.
        question_resp = self.client.post("/api/equivalency-queries/", {
            "credential": credential_id,
            "question_text": "Does this transcript cover material equivalent to our CS301 (Data Structures) course?",
        })
        self.assertEqual(question_resp.status_code, status.HTTP_201_CREATED, question_resp.data)
        self.assertTrue(question_resp.data["answer_text"])
        self.assertGreater(len(question_resp.data["retrieved_chunk_ids"]), 0)

        # The retrieved chunk ids should reference chunks that actually
        # belong to this credential's processed data.
        retrieved_ids = set(question_resp.data["retrieved_chunk_ids"])
        actual_ids = set(chunk.id for chunk in chunks)
        self.assertTrue(retrieved_ids.issubset(actual_ids))

        # 4. History is retrievable.
        history_resp = self.client.get("/api/equivalency-queries/")
        self.assertEqual(history_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(history_resp.data["count"], 1)
