
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from grants.models import Request
from grants.permissions import can_manage_fund_transfers, can_view_request
from .forms import FundTransferForm
from .models import FundTransfer, FundTransferDocument

@login_required
def add_fund_transfer(request, pk):
    if not can_manage_fund_transfers(request.user):
        raise PermissionDenied

    req = get_object_or_404(Request, pk=pk)

    if req.status != Request.Status.APPROVED:
        messages.error(request, "You can only add funds to approved requests.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = FundTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.request = req
            transfer.save()
            messages.success(request, "Fund transfer added successfully.")
            return redirect("fund_transfer_documents", transfer_pk=transfer.pk)
    else:
        form = FundTransferForm(initial={
            'amount': req.requested_amount,
            'classification': req.classification
        })

    return render(request, 'finance/add_fund_transfer.html', {'form': form, 'req': req})


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

@login_required
def fund_transfer_documents(request, transfer_pk):
    transfer = get_object_or_404(
        FundTransfer.objects.select_related("request"),
        pk=transfer_pk,
    )

    req = transfer.request

    if not (
        can_view_request(request.user, req)
        or can_manage_fund_transfers(request.user)
    ):
        raise PermissionDenied

    # Allow viewing documents at both stages.
    if req.status not in [
        Request.Status.APPROVED,
        Request.Status.TRANSFERRED,
    ]:
        messages.error(
            request,
            "Transfer documents are not available at this stage.",
        )
        return redirect("dashboard")

    uploaded_documents = transfer.documents.all()

    for document in uploaded_documents:
        document.download_url = reverse(
            "download_fund_transfer_document",
            kwargs={
                "transfer_pk": transfer.pk,
                "document_pk": document.pk,
            },
        )
        document.tag_url = reverse(
            "tag_fund_transfer_document",
            kwargs={
                "transfer_pk": transfer.pk,
                "document_pk": document.pk,
            },
        )
        document.delete_url = reverse(
            "delete_fund_transfer_document",
            kwargs={
                "transfer_pk": transfer.pk,
                "document_pk": document.pk,
            },
        )

    return render(
        request,
        "finance/fund_transfer_documents.html",
        {
            "req": req,
            "transfer": transfer,
            "uploaded_documents": uploaded_documents,
            "upload_url": reverse(
                "upload_fund_transfer_documents",
                kwargs={"transfer_pk": transfer.pk},
            ),
            "document_tag_choices": FundTransferDocument.TAG_CHOICES,
            "read_only": (
                req.status == Request.Status.TRANSFERRED
                or not can_manage_fund_transfers(request.user)
            ),
        },
    )


@login_required
def download_fund_transfer_document(request, transfer_pk, document_pk):
    transfer = get_object_or_404(
        FundTransfer.objects.select_related("request"),
        pk=transfer_pk,
    )
    if not (
        can_view_request(request.user, transfer.request)
        or can_manage_fund_transfers(request.user)
    ):
        raise PermissionDenied

    if transfer.request.status not in [
        Request.Status.APPROVED,
        Request.Status.TRANSFERRED,
    ]:
        raise PermissionDenied

    document = get_object_or_404(
        FundTransferDocument,
        pk=document_pk,
        transfer=transfer,
    )
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=Path(document.file.name).name,
    )


@login_required
@require_POST
def upload_fund_transfer_documents(request, transfer_pk):
    transfer = get_object_or_404(
        FundTransfer.objects.select_related("request"),
        pk=transfer_pk,
    )

    if not can_manage_fund_transfers(request.user):
        raise PermissionDenied

    if transfer.request.status != Request.Status.APPROVED:
        raise PermissionDenied

    files = request.FILES.getlist("documents")

    if not files:
        messages.error(request, "Please select at least one document.")
        return redirect(
            "fund_transfer_documents",
            transfer_pk=transfer.pk,
        )

    invalid_files = []
    for uploaded_file in files:
        if Path(uploaded_file.name).suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
            invalid_files.append(uploaded_file.name)

    if invalid_files:
        messages.error(
            request,
            "Unsupported file type: " + ", ".join(invalid_files),
        )
        return redirect(
            "fund_transfer_documents",
            transfer_pk=transfer.pk,
        )

    for uploaded_file in files:
        FundTransferDocument.objects.create(
            transfer=transfer,
            file=uploaded_file,
        )

    messages.success(request, "Transfer documents uploaded successfully.")
    return redirect(
        "fund_transfer_documents",
        transfer_pk=transfer.pk,
    )


@login_required
@require_POST
def tag_fund_transfer_document(request, transfer_pk, document_pk):
    transfer = get_object_or_404(FundTransfer, pk=transfer_pk)

    if not can_manage_fund_transfers(request.user):
        raise PermissionDenied

    if transfer.request.status != Request.Status.APPROVED:
        raise PermissionDenied

    document = get_object_or_404(
        FundTransferDocument,
        pk=document_pk,
        transfer=transfer,
    )

    allowed_tags = dict(FundTransferDocument.TAG_CHOICES)
    tag = request.POST.get("tag", "")

    if tag and tag not in allowed_tags:
        messages.error(request, "Please select a valid document tag.")
    else:
        document.tag = tag
        document.save(update_fields=["tag"])
        messages.success(request, "Document tag updated.")

    return redirect(
        "fund_transfer_documents",
        transfer_pk=transfer.pk,
    )


@login_required
@require_POST
def delete_fund_transfer_document(request, transfer_pk, document_pk):
    transfer = get_object_or_404(FundTransfer, pk=transfer_pk)

    if not can_manage_fund_transfers(request.user):
        raise PermissionDenied

    if transfer.request.status != Request.Status.APPROVED:
        raise PermissionDenied

    document = get_object_or_404(
        FundTransferDocument,
        pk=document_pk,
        transfer=transfer,
    )

    document.file.delete(save=False)
    document.delete()

    messages.success(request, "Transfer document deleted.")
    return redirect(
        "fund_transfer_documents",
        transfer_pk=transfer.pk,
    )
