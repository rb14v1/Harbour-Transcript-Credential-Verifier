from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_login_refresh_me_flow(self):
        register_resp = self.client.post("/api/auth/register/", {
            "email": "new.reviewer@example.com",
            "full_name": "New Reviewer",
            "role": "admissions_reviewer",
            "password": "StrongPass123!",
        })
        self.assertEqual(register_resp.status_code, status.HTTP_201_CREATED, register_resp.data)

        login_resp = self.client.post("/api/auth/login/", {
            "email": "new.reviewer@example.com",
            "password": "StrongPass123!",
        })
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_resp.data)
        self.assertIn("refresh", login_resp.data)

        refresh_resp = self.client.post("/api/auth/refresh/", {"refresh": login_resp.data["refresh"]})
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_resp.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        me_resp = self.client.get("/api/auth/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data["email"], "new.reviewer@example.com")

    def test_login_rejects_bad_password(self):
        User.objects.create_user(email="someone@example.com", password="CorrectPass123!")
        resp = self.client.post("/api/auth/login/", {"email": "someone@example.com", "password": "wrong"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_me_is_rejected(self):
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
