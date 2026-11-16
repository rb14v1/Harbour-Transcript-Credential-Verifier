from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applicants.models import Applicant

User = get_user_model()


class ApplicantApiTests(APITestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(email="rev@example.com", password="Pass1234!", role=User.Role.ADMISSIONS_REVIEWER)
        self.admin = User.objects.create_user(email="adm@example.com", password="Pass1234!", role=User.Role.ADMIN)

    def auth(self, user):
        resp = self.client.post("/api/auth/login/", {"email": user.email, "password": "Pass1234!"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_unauthenticated_cannot_list(self):
        resp = self.client.get("/api/applicants/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reviewer_can_create_and_list(self):
        self.auth(self.reviewer)
        baseline_count = Applicant.objects.count()  # seed-data migration may have pre-existing rows

        create_resp = self.client.post("/api/applicants/", {"full_name": "Jamie Doe", "email": "jamie@example.com"})
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED, create_resp.data)

        list_resp = self.client.get("/api/applicants/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(list_resp.data["count"], baseline_count + 1)

    def test_reviewer_cannot_delete(self):
        applicant = Applicant.objects.create(full_name="Jamie Doe", email="jamie2@example.com")
        self.auth(self.reviewer)
        resp = self.client.delete(f"/api/applicants/{applicant.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Applicant.objects.filter(id=applicant.id).exists())

    def test_admin_can_delete(self):
        applicant = Applicant.objects.create(full_name="Jamie Doe", email="jamie3@example.com")
        self.auth(self.admin)
        resp = self.client.delete(f"/api/applicants/{applicant.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Applicant.objects.filter(id=applicant.id).exists())
