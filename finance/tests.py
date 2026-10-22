from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from finance.models import Classification, FundTransfer, FundTransferDocument
from grants.models import Beneficiary, Request


class TransferAuthorizationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="request-owner",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="unrelated",
            password="test-password",
        )
        self.transfer_manager = user_model.objects.create_user(
            username="treasurer",
            password="test-password",
            can_manage_fund_transfers=True,
        )
        self.admin_without_transfer_access = user_model.objects.create_superuser(
            username="admin-without-transfer-access",
            password="test-password",
            email="admin@example.com",
        )
        self.classification = Classification.objects.create(name="Test classification")
        beneficiary = Beneficiary.objects.create(
            full_name="Test Beneficiary",
            contact_number="1234567890",
            address="Test address",
            bank_account_details="Test bank details",
        )
        self.request = Request.objects.create(
            requester=self.owner,
            beneficiary=beneficiary,
            reason_for_assistance="Test request",
            requested_amount=Decimal("100.00"),
            status=Request.Status.APPROVED,
        )
        self.transfer = FundTransfer.objects.create(
            request=self.request,
            amount=Decimal("100.00"),
            transfer_date="2026-10-22",
            transaction_reference="test-reference",
        )

    def test_transfer_manager_can_manage_transfers_without_request_detail_access(self):
        detail_url = reverse("request_detail", args=[self.request.pk])
        add_url = reverse("add_fund_transfer", args=[self.request.pk])
        documents_url = reverse(
            "fund_transfer_documents",
            args=[self.transfer.pk],
        )

        self.client.force_login(self.transfer_manager)
        self.assertEqual(self.client.get(detail_url).status_code, 403)
        self.assertEqual(self.client.get(add_url).status_code, 200)
        self.assertEqual(self.client.get(documents_url).status_code, 200)

    def test_transfer_manager_can_create_a_transfer(self):
        add_url = reverse("add_fund_transfer", args=[self.request.pk])

        self.client.force_login(self.transfer_manager)
        response = self.client.post(
            add_url,
            {
                "amount": "100.00",
                "transfer_date": "2026-10-22",
                "classification": str(self.classification.pk),
                "transaction_reference": "new-reference",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(FundTransfer.objects.filter(request=self.request).count(), 2)

    def test_transfer_document_download_obeys_document_visibility(self):
        media_directory = TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media_directory.name))
        document = FundTransferDocument.objects.create(
            transfer=self.transfer,
            file=SimpleUploadedFile("receipt.pdf", b"test file"),
        )
        url = reverse(
            "download_fund_transfer_document",
            args=[self.transfer.pk, document.pk],
        )

        self.client.force_login(self.transfer_manager)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_unrelated_user_cannot_access_transfer_records_or_documents(self):
        add_url = reverse("add_fund_transfer", args=[self.request.pk])
        documents_url = reverse(
            "fund_transfer_documents",
            args=[self.transfer.pk],
        )

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(add_url).status_code, 403)
        self.assertEqual(self.client.get(documents_url).status_code, 403)

    def test_staff_and_superuser_need_explicit_transfer_permission(self):
        add_url = reverse("add_fund_transfer", args=[self.request.pk])
        complete_url = reverse("process_transfer", args=[self.request.pk])
        dashboard_url = reverse("dashboard")

        self.client.force_login(self.admin_without_transfer_access)
        self.assertEqual(self.client.get(add_url).status_code, 403)
        self.assertEqual(self.client.post(complete_url).status_code, 403)
        response = self.client.get(dashboard_url)
        self.assertNotContains(response, "Approved Requests for Transfer")

    def test_only_transfer_managers_can_change_transfer_documents(self):
        upload_url = reverse(
            "upload_fund_transfer_documents",
            args=[self.transfer.pk],
        )
        tag_url = reverse(
            "tag_fund_transfer_document",
            args=[self.transfer.pk, 999],
        )
        delete_url = reverse(
            "delete_fund_transfer_document",
            args=[self.transfer.pk, 999],
        )

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.post(upload_url).status_code, 403)
        self.assertEqual(self.client.post(tag_url).status_code, 403)
        self.assertEqual(self.client.post(delete_url).status_code, 403)
