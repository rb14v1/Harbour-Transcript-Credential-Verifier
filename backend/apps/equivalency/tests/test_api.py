from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applicants.models import Applicant
from apps.common import search_store
from apps.credentials import services
from apps.credentials.models import Credential
from apps.equivalency.models import EquivalencyQuery

User = get_user_model()


class EquivalencyQueryApiTests(APITestCase):
    def setUp(self):
        search_store.clear_index(services.SEARCH_INDEX_NAME)
        self.reviewer = User.objects.create_user(email="rev3@example.com", password="Pass1234!", role=User.Role.ADMISSIONS_REVIEWER)
        self.reviewer2 = User.objects.create_user(email="rev4@example.com", password="Pass1234!", role=User.Role.ADMISSIONS_REVIEWER)
        self.admin = User.objects.create_user(email="adm3@example.com", password="Pass1234!", role=User.Role.ADMIN)

        applicant = Applicant.objects.create(full_name="Jamie Doe", email="jamie.eq@example.com")
        self.credential = Credential.objects.create(
            applicant=applicant, institution="Test University", credential_type="transcript",
        )

    def auth(self, user):
        resp = self.client.post("/api/auth/login/", {"email": user.email, "password": "Pass1234!"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_reviewer_can_ask_question_and_gets_answer(self):
        self.auth(self.reviewer)
        resp = self.client.post("/api/equivalency-queries/", {
            "credential": self.credential.id,
            "question_text": "Does this cover CS301-equivalent material?",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertTrue(resp.data["answer_text"])
        self.assertEqual(resp.data["reviewer"], self.reviewer.id)

    def test_reviewer_only_sees_own_history(self):
        EquivalencyQuery.objects.create(reviewer=self.reviewer, credential=self.credential, question_text="q1", answer_text="a1")
        EquivalencyQuery.objects.create(reviewer=self.reviewer2, credential=self.credential, question_text="q2", answer_text="a2")

        self.auth(self.reviewer)
        resp = self.client.get("/api/equivalency-queries/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["question_text"], "q1")

    def test_admin_sees_all_history(self):
        baseline_count = EquivalencyQuery.objects.count()  # seed-data migration may have pre-existing rows
        EquivalencyQuery.objects.create(reviewer=self.reviewer, credential=self.credential, question_text="q1", answer_text="a1")
        EquivalencyQuery.objects.create(reviewer=self.reviewer2, credential=self.credential, question_text="q2", answer_text="a2")

        self.auth(self.admin)
        resp = self.client.get("/api/equivalency-queries/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], baseline_count + 2)
