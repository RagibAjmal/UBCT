from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from allauth.socialaccount.models import SocialAccount


class SocialAccountPasswordTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="google-user",
            email="google-user@example.com",
        )
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.social_account = SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-user-123",
        )
        self.client.force_login(self.user)

    def test_google_user_can_set_password_without_current_password(self):
        response = self.client.get(reverse("account_set_password"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set a password")
        self.assertContains(response, "alongside your Google account")
        self.assertNotContains(response, 'name="oldpassword"')

        response = self.client.post(
            reverse("account_set_password"),
            {
                "password1": "UbcTest!9362-Secret",
                "password2": "UbcTest!9362-Secret",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_usable_password())
        self.assertTrue(self.user.check_password("UbcTest!9362-Secret"))
        self.assertTrue(
            SocialAccount.objects.filter(pk=self.social_account.pk, user=self.user).exists()
        )

        self.client.logout()
        login_response = self.client.post(
            reverse("account_login"),
            {
                "login": self.user.username,
                "password": "UbcTest!9362-Secret",
            },
        )
        self.assertRedirects(
            login_response,
            reverse("dashboard"),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_password_change_link_redirects_google_user_to_set_password(self):
        response = self.client.get(reverse("account_change_password"))

        self.assertRedirects(
            response,
            reverse("account_set_password"),
            fetch_redirect_response=False,
        )

    def test_account_menu_offers_set_password_for_google_user(self):
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, reverse("account_set_password"))
        self.assertContains(response, "Set Password")
