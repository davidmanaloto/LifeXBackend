import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

logger = logging.getLogger(__name__)

def send_staff_invitation_email(invitation, request=None):
    """
    Send an invitation email to a newly provisioned staff member.
    """
    user = invitation.user
    token = invitation.token
    
    # Construct activation URL
    # In production, use the actual domain. For dev, we use localhost/base URL.
    if request:
        base_url = f"{request.scheme}://{request.get_host()}"
    else:
        base_url = "http://localhost:8000" # Fallback
        
    activation_url = f"{base_url}/activate-staff/{token}/"
    
    subject = "Welcome to the LifeX Medical Team - Account Activation"
    message = f"""
    Hi {user.first_name},

    An account has been provisioned for you on LifeX as a {user.role}.
    
    To activate your account and set your password, please click the link below:
    {activation_url}
    
    Note: This link will expire in 48 hours.
    
    If you did not expect this, please ignore this email.
    
    Regards,
    The LifeX Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Invitation email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send invitation email to {user.email}: {e}")
        return False
