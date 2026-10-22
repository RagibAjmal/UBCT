from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from finance.models import FundTransfer
from grants.models import ApprovalSignOff, Beneficiary, Request, RequestDocument


class GrantAuthorizationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="other",
            password="test-password",
        )
        self.approver = user_model.objects.create_user(
            username="approver",
            password="test-password",
            can_approve_requests=True,
        )
        self.staff_user = user_model.objects.create_user(
            username="staff",
            password="test-password",
            is_staff=True,
        )
        self.transfer_manager = user_model.objects.create_user(
            username="treasurer",
            password="test-password",
            can_manage_fund_transfers=True,
        )
        self.beneficiary = Beneficiary.objects.create(
            full_name="Test Beneficiary",
            contact_number="1234567890",
            address="Test address",
            bank_account_details="Test bank details",
        )
        self.pending_request = self.create_request(Request.Status.PENDING)
        self.approved_request = self.create_request(Request.Status.APPROVED)
        self.draft_request = self.create_request(
            Request.Status.DRAFT,
            requester=self.other_user,
        )

    def create_request(self, status, requester=None):
        return Request.objects.create(
            requester=requester or self.owner,
            beneficiary=self.beneficiary,
            reason_for_assistance="Test request",
            requested_amount=Decimal("100.00"),
            status=status,
        )

    def test_request_detail_is_limited_to_owner_approvers_and_staff(self):
        url = reverse("request_detail", args=[self.pending_request.pk])

        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 200)

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.approver)
        self.assertEqual(self.client.get(url).status_code, 200)

        self.client.force_login(self.staff_user)
        self.assertEqual(self.client.get(url).status_code, 200)

        self.client.force_login(self.transfer_manager)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_transfer_manager_dashboard_lists_approved_requests(self):
        self.client.force_login(self.transfer_manager)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved Requests for Transfer")
        self.assertContains(response, self.approved_request.request_id)

    def test_only_request_owner_can_edit_draft(self):
        url = reverse("edit_request", args=[self.draft_request.pk])

        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_only_approvers_can_approve_requests(self):
        url = reverse("approve_request", args=[self.pending_request.pk])

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertFalse(
            ApprovalSignOff.objects.filter(request=self.pending_request).exists()
        )

        self.client.force_login(self.approver)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(
            ApprovalSignOff.objects.filter(
                request=self.pending_request,
                approver=self.approver,
            ).exists()
        )

        self.pending_request.status = Request.Status.PENDING
        self.pending_request.save(update_fields=["status"])
        self.client.force_login(self.staff_user)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(
            ApprovalSignOff.objects.filter(
                request=self.pending_request,
                approver=self.staff_user,
            ).exists()
        )

    def test_request_document_download_uses_request_visibility_rules(self):
        media_directory = TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media_directory.name))
        document = RequestDocument.objects.create(
            request=self.pending_request,
            file=SimpleUploadedFile("support.pdf", b"test file"),
        )
        url = reverse(
            "download_request_document",
            args=[self.pending_request.pk, document.pk],
        )

        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_only_transfer_managers_can_complete_requests(self):
        url = reverse("process_transfer", args=[self.approved_request.pk])

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.post(url).status_code, 403)

        FundTransfer.objects.create(
            request=self.approved_request,
            amount=Decimal("100.00"),
            transfer_date="2026-10-22",
            transaction_reference="test-reference",
        )
        self.client.force_login(self.transfer_manager)
        self.assertEqual(self.client.post(url).status_code, 302)

        self.approved_request.refresh_from_db()
        self.assertEqual(self.approved_request.status, Request.Status.TRANSFERRED)
