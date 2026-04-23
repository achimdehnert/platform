import pytest


def test_email_service_smtp_sends(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.IIL_COMMONS = {"EMAIL_PROVIDER": "smtp"}
    settings.DEFAULT_FROM_EMAIL = "noreply@test.com"

    from django.core import mail

    from iil_commons.email.service import EmailMessage, EmailService

    svc = EmailService()
    result = svc.send(
        EmailMessage(
            to=["guest@example.com"],
            subject="Test Subject",
            body="Hello!",
            html_body="<p>Hello!</p>",
        )
    )

    assert result is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Test Subject"
    assert mail.outbox[0].to == ["guest@example.com"]


def test_email_service_smtp_failure_returns_false(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.IIL_COMMONS = {"EMAIL_PROVIDER": "smtp"}

    from unittest.mock import patch

    from iil_commons.email.service import EmailMessage, EmailService

    svc = EmailService()
    with patch(
        "django.core.mail.EmailMultiAlternatives.send",
        side_effect=Exception("SMTP error"),
    ):
        result = svc.send(
            EmailMessage(to=["x@x.com"], subject="S", body="B")
        )
    assert result is False


def test_email_service_resend_missing_package(settings):
    settings.IIL_COMMONS = {"EMAIL_PROVIDER": "resend"}

    from unittest.mock import patch

    from iil_commons.email.service import EmailMessage, EmailService

    svc = EmailService()
    with patch.dict("sys.modules", {"resend": None}):
        result = svc.send(EmailMessage(to=["x@x.com"], subject="S", body="B"))
    assert result is False
