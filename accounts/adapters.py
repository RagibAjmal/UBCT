import logging

from django.conf import settings

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


logger = logging.getLogger(__name__)


class UBCTSocialAccountAdapter(DefaultSocialAccountAdapter):
    def on_authentication_error(
        self,
        request,
        provider,
        error=None,
        exception=None,
        extra_context=None,
    ):
        if settings.DEBUG:
            exception_type = type(exception).__name__ if exception else "none"
            logger.warning(
                "Social sign-in failed: provider=%s error=%s exception_type=%s",
                provider.id,
                error,
                exception_type,
            )

        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )
