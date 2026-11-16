from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")

    def test_create_user_sets_hashed_password(self):
        user = User.objects.create_user(email="person@example.com", password="StrongPass123!")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(user.role, User.Role.ADMISSIONS_REVIEWER)

    def test_create_superuser_is_admin(self):
        user = User.objects.create_superuser(email="root@example.com", password="StrongPass123!")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_admin)

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertFalse(hasattr(User, "username"))
