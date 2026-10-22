import hashlib
from pathlib import Path
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from core.models import SystemSetting
from django.views.decorators.http import require_POST

from grants.utils import send_whatsapp_message
from .forms import BeneficiaryForm, RequestForm
from finance.models import FundTransfer
from .models import ApprovalSignOff, Request, RequestDocument
from grants.permissions import (
    can_approve_requests,
    can_manage_fund_transfers,
    can_view_request,
)

@login_required
def dashboard(request):
    # 1. Fetch requests created by the logged-in user
    my_requests = Request.objects.filter(requester=request.user).order_by('-id')
    
    # Fetch all requests currently waiting for approval.
    if can_approve_requests(request.user):
        pending_approvals = Request.objects.filter(
            status=Request.Status.PENDING
        )
    else:
        pending_approvals = []

    can_manage_transfers = can_manage_fund_transfers(request.user)
    if can_manage_transfers:
        transfer_requests = (
            Request.objects.filter(status=Request.Status.APPROVED)
            .select_related("requester", "beneficiary")
            .prefetch_related("fundtransfer_set")
            .order_by("-pk")
        )
    else:
        transfer_requests = []
    
    return render(request, 'grants/dashboard.html', {
        'my_requests': my_requests,
        'pending_approvals': pending_approvals,
        'can_review_approvals': can_approve_requests(request.user),
        'can_manage_transfers': can_manage_transfers,
        'transfer_requests': transfer_requests,
    })


@login_required
def create_request(request):
    if request.method == "POST":
        form = RequestForm(request.POST)

        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.requester = request.user

            action = request.POST.get("action")

            if action == "submit":
                new_request.status = Request.Status.DOCUMENTS_REQUIRED
                messages.success(
                    request,
                    "Request created. You can now upload documents and request approval."
                )
            else:
                new_request.status = Request.Status.DRAFT
                messages.success(request, "Request saved as a draft.")

            new_request.save()
            return redirect("request_detail", pk=new_request.pk)
    else:
        form = RequestForm()

    timeline_steps = [
        {"number": 1, "label": "Draft"},
        {"number": 2, "label": "Documents Needed"},
        {"number": 3, "label": "Awaiting Approval"},
        {"number": 4, "label": "Approved for Payment"},
        {"number": 5, "label": "Funds Transferred"},
    ]

    draft_request = Request(requester=request.user, status=Request.Status.DRAFT)

    return render(
        request,
        "grants/request_detail.html",
        {
            "req": draft_request,
            "is_create_request": True,
            "form": form,
            "form_action": reverse("create_request"),
            "edit_url": reverse("create_request"),
            "submit_label": "Create Request →",
            "has_approved": False,
            "uploaded_documents": [],
            "timeline_steps": timeline_steps,
            "current_step": 1,
            "can_edit_request": True,
            "can_manage_transfers": False,
        },
    )


@login_required
def create_beneficiary(request):
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url and not (
        next_url.startswith("/")
        and not next_url.startswith("//")
        and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts=set(),
            require_https=request.is_secure(),
        )
    ):
        next_url = None

    if request.method == 'POST':
        form = BeneficiaryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Beneficiary added successfully.")
            
            # Redirect to the 'next' URL if provided, otherwise fallback to the dashboard
            if next_url:
                return redirect(next_url)
            return redirect('dashboard') 
    else:
        form = BeneficiaryForm()

    return render(request, 'grants/create_beneficiary.html', { # adjust template path if needed
        'form': form, 
        'next_url': next_url
    })


@login_required
def edit_request(request, pk):
    req = get_object_or_404(Request, pk=pk)

    if req.requester_id != request.user.pk:
        raise PermissionDenied

    # Security check: Only allow editing if the request is actually a draft
    if req.status != Request.Status.DRAFT:
        messages.error(request, "Only draft requests can be edited.")
        return redirect('request_detail', pk=pk)

    if request.method == 'POST':
        # Bind the existing instance to the form along with new POST data
        form = RequestForm(request.POST, request.FILES, instance=req)
        
        if form.is_valid():
            updated_request = form.save(commit=False)
            
            # Identify which button the user clicked
            action = request.POST.get('action')
            
            if action == 'submit':
                updated_request.status = Request.Status.DOCUMENTS_REQUIRED
                messages.success(request, f"Request updated and submitted for document upload successfully.")
            else:
                updated_request.status = Request.Status.DRAFT
                messages.success(request, "Draft updated successfully.")
                
            updated_request.save()
            return redirect('request_detail', pk=pk)
            
    # If a GET request accidentally hits this URL, send them back to the detail page
    return redirect('request_detail', pk=pk)

@login_required
@require_POST
def process_transfer(request, pk):
    if not can_manage_fund_transfers(request.user):
        raise PermissionDenied

    req = get_object_or_404(Request, pk=pk)

    if req.status != Request.Status.APPROVED:
        messages.error(request, "Only approved requests can be marked as transferred.")
        return redirect('dashboard')

    if not req.fundtransfer_set.exists():
        messages.error(request, "You must add at least one fund transfer record before marking as complete.")
        return redirect('dashboard')

    total_transferred = req.fundtransfer_set.aggregate(Sum('amount'))['amount__sum'] or 0
    if total_transferred < req.requested_amount:
        messages.warning(request, f"Note: Total transferred (₹{total_transferred}) is less than the requested amount (₹{req.requested_amount}).")

    req.status = Request.Status.TRANSFERRED
    req.save()
    messages.success(request, "Request successfully marked as transferred and closed.")
    return redirect('dashboard')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

@login_required
@require_POST
def approve_request(request, pk):
    if not can_approve_requests(request.user):
        raise PermissionDenied

    req = get_object_or_404(Request, pk=pk)

    if req.status != Request.Status.PENDING:
        messages.error(request, "This request is not pending approval.")
        return redirect('request_detail', pk=pk)

    if ApprovalSignOff.objects.filter(request=req, approver=request.user).exists():
        messages.warning(request, "You have already approved this request.")
        return redirect('request_detail', pk=pk)

    raw_string = f"{req.pk}-{request.user.pk}-{timezone.now().isoformat()}"
    crypto_hash = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

    ApprovalSignOff.objects.create(
        request=req,
        approver=request.user,
        ip_address=get_client_ip(request),
        cryptographic_hash=crypto_hash
    )

    try:
        setting = SystemSetting.objects.get(key='MIN_APPROVALS')
        min_approvals = int(setting.value)
    except (SystemSetting.DoesNotExist, ValueError):
        min_approvals = 2

    current_approvals_count = req.approvalsignoff_set.count()

    if current_approvals_count >= min_approvals:
        req.status = Request.Status.APPROVED
        req.save()
        messages.success(request, f"Request approved! Threshold of {min_approvals} approvals reached. Status is now APPROVED.")
        # send_whatsapp_message(settings.APPROVER_PHONE_NUMBER, msg)
    else:
        messages.success(request, f"Approval logged. ({current_approvals_count}/{min_approvals} approvals reached).")

    return redirect('request_detail', pk=pk)


@login_required
@require_POST
def upload_request_documents(request, pk):
    req = get_object_or_404(Request, pk=pk)

    # Only the person who raised the request can upload its documents.
    if req.requester_id != request.user.pk:
        return HttpResponseForbidden("You cannot upload documents for this request.")

    if req.status != Request.Status.DOCUMENTS_REQUIRED:
        messages.error(
            request,
            "Documents can only be uploaded during the Documents Required stage."
        )
        return redirect("request_detail", pk=req.pk)

    files = request.FILES.getlist("documents")

    if not files:
        messages.error(request, "Please select at least one document to upload.")
        return redirect("request_detail", pk=req.pk)

    max_document_count = 10
    max_batch_size = 25 * 1024 * 1024
    existing_document_count = RequestDocument.objects.filter(request=req).count()

    if existing_document_count + len(files) > max_document_count:
        messages.error(request, "A request can have at most 10 supporting documents.")
        return redirect("request_detail", pk=req.pk)

    if sum(uploaded_file.size for uploaded_file in files) > max_batch_size:
        messages.error(request, "The combined upload size cannot exceed 25 MiB.")
        return redirect("request_detail", pk=req.pk)

    file_field = RequestDocument._meta.get_field("file")
    validation_errors = []
    for uploaded_file in files:
        try:
            file_field.run_validators(uploaded_file)
        except ValidationError as error:
            validation_errors.extend(
                f"{uploaded_file.name}: {message}"
                for message in error.messages
            )

    if validation_errors:
        for error in validation_errors:
            messages.error(request, error)
        return redirect("request_detail", pk=req.pk)

    for uploaded_file in files:
        RequestDocument.objects.create(
            request=req,
            file=uploaded_file,
            tag="General",
        )

    messages.success(request, "Document(s) uploaded successfully.")
    return redirect("request_detail", pk=req.pk)


@login_required
@require_POST
def submit_for_approval(request, pk):
    req = get_object_or_404(Request, pk=pk)

    # Only the requester can submit their request.
    if req.requester_id != request.user.pk:
        return HttpResponseForbidden(
            "You cannot submit this request for approval."
        )

    # Only requests in this stage can be submitted.
    if req.status != Request.Status.DOCUMENTS_REQUIRED:
        messages.error(
            request,
            "This request is not ready for approval submission."
        )
        return redirect("request_detail", pk=req.pk)

    # Require at least one uploaded document.
    has_documents = RequestDocument.objects.filter(
        request=req
    ).exists()

    if not has_documents:
        messages.error(
            request,
            "Please upload at least one supporting document before requesting approval."
        )
        return redirect("request_detail", pk=req.pk)

    # All checks passed; move the request to Pending Approval.
    req.status = Request.Status.PENDING
    req.save(update_fields=["status"])

    messages.success(
        request,
        "Request submitted for approval successfully."
    )
    return redirect("request_detail", pk=req.pk)



@login_required
def request_detail(request, pk):
    req = get_object_or_404(
        Request.objects.prefetch_related(
            Prefetch(
                "fundtransfer_set",
                queryset=FundTransfer.objects.annotate(
                    document_count=Count("documents")
                ),
            )
        ),
        pk=pk,
    )

    if not can_view_request(request.user, req):
        raise PermissionDenied

    # Check whether the current user has already approved this request.
    has_approved = req.approvalsignoff_set.filter(
        approver=request.user
    ).exists()

    # Retrieve supporting documents for this request.
    uploaded_documents = RequestDocument.objects.filter(request=req)
    for document in uploaded_documents:
        document.download_url = reverse(
            "download_request_document",
            kwargs={"pk": req.pk, "document_pk": document.pk},
        )

    # Define the request progress timeline.
    timeline_steps = [
        {"number": 1, "label": "Draft"},
        {"number": 2, "label": "Documents Needed"},
        {"number": 3, "label": "Awaiting Approval"},
        {"number": 4, "label": "Approved for Payment"},
        {"number": 5, "label": "Funds Transferred"},
    ]

    current_step = {
        Request.Status.DRAFT: 1,
        Request.Status.DOCUMENTS_REQUIRED: 2,
        Request.Status.PENDING: 3,
        Request.Status.APPROVED: 4,
        Request.Status.TRANSFERRED: 5,
    }.get(req.status, 1)

    # Build one context dictionary so no variables are overwritten.
    context = {
        "req": req,
        "has_approved": has_approved,
        "uploaded_documents": uploaded_documents,
        "timeline_steps": timeline_steps,
        "current_step": current_step,
        "edit_url": reverse("edit_request", kwargs={"pk": req.pk}),
        "can_edit_request": req.requester_id == request.user.pk,
        "can_review_approvals": can_approve_requests(request.user),
        "can_manage_transfers": can_manage_fund_transfers(request.user),
    }

    # Provide the existing request instance to the reusable draft form.
    if req.status == Request.Status.DRAFT and req.requester_id == request.user.pk:
        context["form"] = RequestForm(instance=req)

    if req.status == Request.Status.DOCUMENTS_REQUIRED:
        for document in uploaded_documents:
            document.tag_url = reverse(
                "tag_request_document",
                kwargs={
                    "pk": req.pk,
                    "document_pk": document.pk,
                },
            )
            document.delete_url = reverse(
                "delete_request_document",
                kwargs={
                    "pk": req.pk,
                    "document_pk": document.pk,
                },
            )

        context.update({
            "upload_url": reverse(
                "upload_request_documents",
                kwargs={"pk": req.pk},
            ),
            "document_tag_choices": [
                ("General", "Supporting document"),
                ("IDENTITY", "Identity Proof"),
                ("INVOICE", "Invoice"),
                ("RECEIPT", "Receipt"),
                ("APPLICATION", "Application"),
                ("OTHER", "Other"),
            ],
        })

    return render(request, "grants/request_detail.html", context)


@login_required
def download_request_document(request, pk, document_pk):
    req = get_object_or_404(Request, pk=pk)
    if not can_view_request(request.user, req):
        raise PermissionDenied

    document = get_object_or_404(
        RequestDocument,
        pk=document_pk,
        request=req,
    )
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=Path(document.file.name).name,
    )


@login_required
def delete_request_document(request, pk, document_pk):
    if request.method != "POST":
        return redirect("request_detail", pk=pk)

    req = get_object_or_404(Request, pk=pk)

    if req.requester_id != request.user.pk:
        raise PermissionDenied

    if req.status != Request.Status.DOCUMENTS_REQUIRED:
        messages.error(request, "Documents cannot be deleted at this stage.")
        return redirect("request_detail", pk=pk)

    document = get_object_or_404(
        RequestDocument,
        pk=document_pk,
        request=req,
    )

    # Remove the stored file as well as its database record.
    document.file.delete(save=False)
    document.delete()

    messages.success(request, "Document deleted successfully.")
    return redirect("request_detail", pk=pk)


@login_required
def tag_request_document(request, pk, document_pk):
    req = get_object_or_404(Request, pk=pk)

    if req.requester_id != request.user.pk:
        raise PermissionDenied

    if req.status != Request.Status.DOCUMENTS_REQUIRED:
        messages.error(request, "Document tags cannot be changed at this stage.")
        return redirect("request_detail", pk=pk)

    document = get_object_or_404(
        RequestDocument,
        pk=document_pk,
        request=req,
    )

    if request.method == "POST":
        allowed_tags = {
            "General", "IDENTITY", "INVOICE", "RECEIPT", "APPLICATION", "OTHER"
        }
        tag = request.POST.get("tag", "")

        if tag and tag not in allowed_tags:
            messages.error(request, "Please select a valid document tag.")
        else:
            document.tag = tag
            document.save(update_fields=["tag"])
            messages.success(request, "Document tag updated.")

    return redirect("request_detail", pk=pk)


@login_required
def all_requests(request):
    # Reviewers can see all requests; other users see only their own.
    can_view_all_requests = can_approve_requests(request.user)
    if can_view_all_requests:
        queryset = Request.objects.select_related("requester")
    else:
        queryset = Request.objects.filter(
            requester=request.user
        ).select_related("requester")

    # Search only fields users are allowed to identify from the request list.
    search_query = request.GET.get("q", "").strip()

    if search_query:
        queryset = queryset.filter(
            Q(request_id__icontains=search_query)
            | Q(beneficiary__full_name__icontains=search_query)
            | Q(requested_for__icontains=search_query)
            | Q(requester__username__icontains=search_query)
            | Q(requester__first_name__icontains=search_query)
            | Q(requester__last_name__icontains=search_query)
        )

    # Apply a status filter only if it is a valid choice.
    selected_status = request.GET.get("status", "")
    valid_statuses = {
        value for value, label in Request.Status.choices
    }

    if selected_status in valid_statuses:
        queryset = queryset.filter(status=selected_status)
    else:
        selected_status = ""

    queryset = queryset.order_by("-pk")

    # Count requests by status for the summary cards.
    visible_requests = (
        Request.objects.all()
        if can_view_all_requests
        else Request.objects.filter(requester=request.user)
    )

    status_counts = [
        {
            "value": value,
            "label": label,
            "count": visible_requests.filter(status=value).count(),
        }
        for value, label in Request.Status.choices
    ]

    paginator = Paginator(queryset, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "requests": page_obj.object_list,
        "search_query": search_query,
        "selected_status": selected_status,
        "status_choices": Request.Status.choices,
        "status_counts": status_counts,
        "total_requests": visible_requests.count(),
    }

    return render(request, "grants/all_requests.html", context)
