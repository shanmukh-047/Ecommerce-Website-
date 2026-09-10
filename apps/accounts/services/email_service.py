"""
Email notification service for Bharat Masala transactional communications.
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Service handling transactional emails with plain text and styled HTML."""

    @staticmethod
    def send_password_reset_email(recipient_email: str, reset_url: str) -> bool:
        """
        Sends a secure password reset link to the specified email address.
        Never logs or includes tokens in application log files.
        """
        subject = "Reset Your Bharat Masala Password"
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Bharat Masala <support@bharathmasala.com>")
        timeout_hours = getattr(settings, "PASSWORD_RESET_TIMEOUT", 3600) // 3600 or 1

        text_content = f"""Hello,

We received a request to reset the password for your Bharat Masala account.

To set a new password, please visit the following link:
{reset_url}

This link is securely time-limited and will expire in {timeout_hours} hour(s). It can only be used once.

If you did not request this password reset, please disregard this email. Your existing password and account remain secure.

Warm regards,
The Bharat Masala Team
Estate-Direct Western Ghats Spices
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Password Reset — Bharat Masala</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #FAF8F5; margin: 0; padding: 24px; color: #1C1917; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E7E5E4; border-radius: 16px; padding: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .logo {{ text-align: center; margin-bottom: 24px; }}
    .logo-badge {{ display: inline-block; background: #D97706; color: #FFFFFF; font-size: 20px; font-weight: bold; width: 44px; height: 44px; line-height: 44px; border-radius: 12px; margin-bottom: 8px; }}
    .brand-title {{ font-size: 20px; font-weight: 800; color: #1C1917; letter-spacing: 0.05em; }}
    h2 {{ font-size: 18px; font-weight: 700; color: #1C1917; margin-top: 0; }}
    p {{ font-size: 14px; line-height: 1.6; color: #44403C; margin: 16px 0; }}
    .button-wrap {{ text-align: center; margin: 28px 0; }}
    .btn {{ display: inline-block; background: #D97706; color: #FFFFFF !important; text-decoration: none; font-size: 14px; font-weight: 700; padding: 12px 28px; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .security-note {{ background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 12px 16px; font-size: 12px; color: #92400E; margin: 24px 0; }}
    .footer {{ text-align: center; font-size: 11px; color: #78716C; margin-top: 32px; border-top: 1px solid #F5F5F4; pt: 16px; }}
    .link-alt {{ font-size: 11px; color: #A8A29E; word-break: break-all; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">
      <div class="logo-badge">B</div>
      <div class="brand-title">BHARAT MASALA</div>
    </div>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>We received a request to reset the password for your account associated with <strong>{recipient_email}</strong>.</p>
    <div class="button-wrap">
      <a href="{reset_url}" class="btn">Reset Password</a>
    </div>
    <div class="security-note">
      <strong>Security notice:</strong> This link will expire in {timeout_hours} hour(s) and can only be used once. If you did not request a password change, no action is needed — your account remains completely safe.
    </div>
    <p class="link-alt">If the button above does not work, copy and paste this link into your browser:<br>{reset_url}</p>
    <div class="footer">
      &copy; Bharat Masala Products. Western Ghats Harvest Heritage. All rights reserved.
    </div>
  </div>
</body>
</html>
"""

        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=[recipient_email],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info("Password reset email dispatched to %s", recipient_email)
            return True
        except Exception as exc:
            logger.error("Failed to send password reset email to %s: %s", recipient_email, str(exc))
            return False
