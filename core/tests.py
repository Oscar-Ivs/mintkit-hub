from django.test import TestCase, override_settings
from django.core.mail import EmailMessage
from django.core import mail


class EmailSendingTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_can_be_sent_via_django_backend(self):
        # Uses locmem backend so no external SMTP is required for tests
        msg = EmailMessage(
            subject="MintKit test email",
            body="If you received this, Django email sending works.",
            from_email="MintKit <no-reply@mg.mintkit.co.uk>",
            to=["test@example.com"],
        )

        sent_count = msg.send()

        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "MintKit test email")
