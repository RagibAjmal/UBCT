from io import StringIO
import re
from types import SimpleNamespace
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import EmailMessage
from django.http import HttpRequest
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.adapters import UBCTSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from core.email_backends import ReadableConsoleEmailBackend


class AccountRegistrationAndRecoveryTests(TestCase):
    def test_console_reset_email_contains_followable_unwrapped_link(self):
        user = get_user_model().objects.create_user(
            username="console-reset-member",
            email="console-reset-member@example.com",
            password="UbcConsole!8274-Password",
        )
        output = StringIO()

        with self.settings(
            MAILERS={
                "default": {
                    "BACKEND": "core.email_backends.ReadableConsoleEmailBackend",
                    "OPTIONS": {"stream": output},
                }
            }
        ):
            response = self.client.post(
                reverse("account_reset_password"),
                {"email": user.email},
            )

        self.assertEqual(response.status_code, 302)
        matches = re.findall(
            r"https?://[^\s<>]+/accounts/password/reset/key/[^\s<>]+",
            output.getvalue(),
        )
        self.assertEqual(len(matches), 1)
        self.assertNotIn("=\n", output.getvalue())

        reset_path = urlparse(matches[0].rstrip(".,)")).path
        reset_response = self.client.get(reset_path, follow=True)
        self.assertEqual(reset_response.status_code, 200)
        self.assertContains(reset_response, "Choose a new password")
        self.assertNotContains(reset_response, "This reset link is invalid")

    def test_console_email_backend_prints_wrapped_reset_url_intact(self):
        reset_url = (
            "http://127.0.0.1:8000/accounts/password/reset/key/"
            "2-dgvntw-3bdf96b9fad2d44f2d6679d21a1e5c78/"
        )
        email = EmailMessage(
            subject="Password reset",
            body=f"Use this link to reset your password:\n\n{reset_url}",
            from_email="portal@example.com",
            to=["member@example.com"],
        )
        stream = StringIO()
        backend = ReadableConsoleEmailBackend(stream=stream)

        backend.write_message(email)

        self.assertIn(reset_url, stream.getvalue())
        self.assertNotIn("=\n", stream.getvalue())

    def test_signup_creates_requester_account_with_email_and_password(self):
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="username"')

        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "new-member@example.com",
                "username": "new-member",
                "password1": "UbcMember!7481-Password",
                "password2": "UbcMember!7481-Password",
            },
        )

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="new-member")
        self.assertEqual(user.email, "new-member@example.com")
        self.assertEqual(user.role, "REQUESTER")
        self.assertTrue(user.has_usable_password())

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    )
    def test_password_reset_sends_email_and_shows_non_disclosing_confirmation(self):
        user = get_user_model().objects.create_user(
            username="reset-member",
            email="reset-member@example.com",
            password="UbcMember!7481-Password",
        )

        response = self.client.get(reverse("account_reset_password"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forgot your password?")

        response = self.client.post(
            reverse("account_reset_password"),
            {"email": user.email},
        )

        self.assertRedirects(
            response,
            reverse("account_reset_password_done"),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        confirmation = self.client.get(reverse("account_reset_password_done"))
        self.assertContains(confirmation, "If an account matches that email address")

    @override_settings(
        MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    )
    def test_password_reset_email_link_opens_reset_form_and_updates_password(self):
        user = get_user_model().objects.create_user(
            username="reset-link-member",
            email="reset-link-member@example.com",
            password="UbcMember!7481-Password",
        )
        self.client.post(
            reverse("account_reset_password"),
            {"email": user.email},
        )
        self.assertEqual(len(mail.outbox), 1)

        email_links = re.findall(r"https?://[^\s<>]+", mail.outbox[0].body)
        reset_link = next(
            link.rstrip(".,)")
            for link in email_links
            if "/accounts/password/reset/key/" in link
        )
        reset_path = urlparse(reset_link).path

        reset_response = self.client.get(reset_path, follow=True)
        self.assertEqual(reset_response.status_code, 200)
        self.assertContains(reset_response, "Choose a new password")
        self.assertNotContains(reset_response, "This reset link is invalid")

        response = self.client.post(
            reset_response.request["PATH_INFO"],
            {
                "password1": "UbcNew!9354-Password",
                "password2": "UbcNew!9354-Password",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("UbcNew!9354-Password"))

    def test_login_page_links_to_signup_and_password_reset(self):
        response = self.client.get(reverse("account_login"))

        self.assertContains(response, reverse("account_signup"))
        self.assertContains(response, reverse("account_reset_password"))


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


class SocialAccountErrorLoggingTests(TestCase):
    @override_settings(DEBUG=True)
    def test_google_callback_logs_when_session_state_is_missing(self):
        with self.assertLogs("accounts.adapters", level="WARNING") as captured:
            response = self.client.get(
                reverse("google_callback"),
                {"state": "missing-state", "code": "test-code"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertIn("provider=google", captured.output[0])
        self.assertIn("exception_type=none", captured.output[0])
        self.assertNotIn("test-code", captured.output[0])

    @override_settings(DEBUG=True)
    def test_logs_safe_callback_diagnostics_without_exception_details(self):
        adapter = UBCTSocialAccountAdapter()
        secret_message = "authorization_code=must-not-be-logged"

        with self.assertLogs("accounts.adapters", level="WARNING") as captured:
            adapter.on_authentication_error(
                HttpRequest(),
                SimpleNamespace(id="google"),
                error="unknown",
                exception=RuntimeError(secret_message),
            )

        self.assertIn("provider=google", captured.output[0])
        self.assertIn("exception_type=RuntimeError", captured.output[0])
        self.assertNotIn(secret_message, captured.output[0])

    @override_settings(DEBUG=False)
    def test_does_not_log_callback_details_outside_debug(self):
        adapter = UBCTSocialAccountAdapter()

        with self.assertNoLogs("accounts.adapters", level="WARNING"):
            adapter.on_authentication_error(
                HttpRequest(),
                SimpleNamespace(id="google"),
                error="unknown",
            )
