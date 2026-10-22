def can_approve_requests(user):
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or getattr(user, "can_approve_requests", False)
    )


def can_manage_fund_transfers(user):
    return user.is_authenticated and (
        getattr(user, "can_manage_fund_transfers", False)
    )


def can_view_request(user, grant_request):
    return user.is_authenticated and (
        grant_request.requester_id == user.pk
        or can_approve_requests(user)
    )
