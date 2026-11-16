from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applicants.models import Applicant
from apps.common import search_store
from apps.credentials import services
from apps.credentials.models import Credential

User = get_user_model()


class CredentialApiTests(APITestCase):
    def setUp(self):
        search_store.clear_index(services.SEARCH_INDEX_NAME)
        self.reviewer = User.objects.create_user(email="rev2@example.com", password="Pass1234!", role=User.Role.ADMISSIONS_REVIEWER)
        self.admin = User.objects.create_user(email="adm2@example.com", password="Pass1234!", role=User.Role.ADMIN)
        self.applicant = Applicant.objects.create(full_name="Jamie Doe", email="jamie.api@example.com")

    def auth(self, user):
        resp = self.client.post("/api/auth/login/", {"email": user.email, "password": "Pass1234!"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_reviewer_can_upload_process_and_view_records(self):
        self.auth(self.reviewer)
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile(
            "transcript.txt",
            b"Data Structures|A|Fall 2021\nComputer Networks|B+|Spring 2022\n",
            content_type="text/plain",
        )
        create_resp = self.client.post("/api/credentials/", {
            "applicant": self.applicant.id,
            "institution": "Test University",
            "credential_type": "transcript",
            "file": upload,
        }, format="multipart")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED, create_resp.data)
        credential_id = create_resp.data["id"]
        self.assertEqual(create_resp.data["status"], "uploaded")
        self.assertTrue(create_resp.data["blob_path"])

        process_resp = self.client.post(f"/api/credentials/{credential_id}/process/")
        self.assertEqual(process_resp.status_code, status.HTTP_200_OK, process_resp.data)
        self.assertEqual(process_resp.data["status"], "processed")
        self.assertEqual(len(process_resp.data["records"]), 2)

        records_resp = self.client.get(f"/api/credentials/{credential_id}/records/")
        self.assertEqual(records_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(records_resp.data), 2)

    def test_process_without_upload_returns_400(self):
        self.auth(self.reviewer)
        credential = Credential.objects.create(
            applicant=self.applicant, institution="X", credential_type="transcript",
        )
        resp = self.client.post(f"/api/credentials/{credential.id}/process/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reviewer_cannot_delete_credential(self):
        credential = Credential.objects.create(
            applicant=self.applicant, institution="X", credential_type="transcript",
        )
        self.auth(self.reviewer)
        resp = self.client.delete(f"/api/credentials/{credential.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_credential(self):
        credential = Credential.objects.create(
            applicant=self.applicant, institution="X", credential_type="transcript",
        )
        self.auth(self.admin)
        resp = self.client.delete(f"/api/credentials/{credential.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter_credentials_by_applicant(self):
        other_applicant = Applicant.objects.create(full_name="Other Person", email="other@example.com")
        Credential.objects.create(applicant=self.applicant, institution="A", credential_type="transcript")
        Credential.objects.create(applicant=other_applicant, institution="B", credential_type="diploma")

        self.auth(self.reviewer)
        resp = self.client.get(f"/api/credentials/?applicant={self.applicant.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
