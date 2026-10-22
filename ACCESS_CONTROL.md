# Roles and access

This document describes the access checks currently enforced by the application.
It is based on the request and finance views, not just on which buttons appear in
the interface.

## Who can see all requests?

Only signed-in users for whom `can_approve_requests` is true can see every
request in **All Requests**. This includes users who are Django staff or
superusers, even if their `can_approve_requests` checkbox is not selected.

Other signed-in users see only their own requests in **All Requests** and on
their dashboard. A transfer manager does not get access to all requests merely
because they can manage transfers.

Request details and request documents are visible to:

- The user who created the request.
- An approver: a user with `can_approve_requests`, Django staff status, or
  superuser status.

An unrelated user cannot access a request by guessing its URL. A transfer
manager who is neither the requester nor an approver cannot open the request
detail page, although they can access the separate transfer actions described
below.

## Permission summary

| Capability | Requester / ordinary user | Approver | Transfer manager | Django staff / superuser |
|---|---|---|---|---|
| Create a request or beneficiary | Yes; sign-in required | Yes | Yes | Yes |
| See all requests and request details | No; own requests only | Yes | No; own requests only | Yes |
| Edit a draft | Only their own draft | Only their own draft | Only their own draft | Only their own draft |
| Upload, tag, or delete request documents | Only for their own request while it is in **Documents Required** | Same owner-only rule | Same owner-only rule | Same owner-only rule |
| Submit their request for approval | Only their own request, with at least one document uploaded | Same owner-only rule | Same owner-only rule | Same owner-only rule |
| Approve a pending request | No | Yes, if `can_approve_requests` is enabled | No, unless separately allowed to approve | Yes |
| View transfer documents | For their own request while it is **Approved** or **Transferred** | For visible requests in those stages | Yes, for transfers in those stages | For visible requests in those stages |
| Add or manage transfer records and documents | No | No, unless separately given transfer permission | Yes | Only if separately given transfer permission |
| Mark an approved request as transferred | No | No, unless separately given transfer permission | Yes | Only if separately given transfer permission |
| Open Django Admin | No | No, unless also Django staff | No, unless also Django staff | Staff can enter subject to admin permissions; superusers have full admin access |

An ordinary user's “own requests” scope does not grant that user access to
another person's request, even if they know its request ID.

## Role labels and permission flags

The account has four role labels:

- **Requester**
- **Approver / Trustee**
- **Administrator**
- **Report Viewer (Auditor)**

These labels are descriptive only; assigning a label does **not** automatically
grant the corresponding permission. The application checks the user's
permission flags and Django account flags instead:

- `can_approve_requests` grants access to all requests and the ability to
  approve pending requests.
- `can_manage_fund_transfers` grants transfer management, including adding
  transfers, changing transfer documents, and completing approved requests.
- Django `is_staff` grants the approval/all-request access above and entry to
  the Django Admin site, subject to the user's admin permissions.
- Django `is_superuser` grants the approval/all-request access above and full
  Django Admin access.

Staff status and superuser status do **not** automatically grant
`can_manage_fund_transfers`. The `ADMIN` role label alone does not grant Django
Admin access or any of these permissions. Likewise, `VIEWER` does not grant a
separate all-request reporting view; without approval access, a viewer sees
only their own requests.

New accounts created through signup default to the **Requester** role and do
not receive either application permission flag.

## Request and transfer workflow restrictions

- Only the request owner can edit a draft.
- Only the owner can upload supporting documents and submit a request for
  approval. Submission requires at least one supporting document.
- Only an approver can record an approval, and only while the request is
  pending. The same approver cannot approve the same request twice. The
  approval threshold is configured by `MIN_APPROVALS`; if that setting is
  absent or invalid, the application uses a default of two approvals.
- Only a transfer manager can add a transfer or mark a request as transferred.
  The request must already be approved, and at least one transfer record must
  exist before it can be completed.
- Transfer managers can add, tag, and delete transfer documents only while a
  request is approved. Transfer documents are read-only after the request is
  transferred.
- Request and transfer document downloads go through permission-checked
  application views.

## Assigning access

An administrator should assign the role label for display and separately
configure the required access flags on the user's account in Django Admin:

1. Set **Can approve requests** only for trusted approvers who should see all
   requests and approve them.
2. Set **Can manage fund transfers** only for trusted finance users who should
   record transfers and complete approved requests.
3. Set Django **Staff status** only for people who need Django Admin access.
   Staff users can also see all requests and approve them, so do not use staff
   status solely to grant admin-site access to someone who must not see or
   approve all requests.
4. Reserve Django **Superuser status** for administrators who need full access.

Granting one application permission does not automatically grant the other.
