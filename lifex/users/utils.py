import pyotp
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

def generate_otp(user):
    """
    Generate a 6-digit OTP for the user
    """
    if not user.otp_base32:
        user.otp_base32 = pyotp.random_base32()
        user.save()
    
    totp = pyotp.TOTP(user.otp_base32, interval=300) # 5 minutes expiry
    return totp.now()

def send_otp_email(user, otp):
    """
    Send OTP via email
    """
    subject = 'Your LifeX Verification Code'
    message = f'Hi {user.first_name or "there"},\n\nYour verification code is: {otp}\n\nThis code will expire in 5 minutes.\n\nIf you did not request this code, please secure your account.'
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    return send_mail(subject, message, email_from, recipient_list)

def send_otp_sms(user, otp):
    """
    Send OTP via SMS using Twilio
    """
    if not user.phone_number:
        logger.error(f"User {user.email} has no phone number for SMS OTP")
        return False
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your LifeX security code is: {otp}. Valid for 5 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=user.phone_number
        )
        return True
    except Exception as e:
        logger.error(f"Error sending SMS to {user.phone_number}: {e}")
        # For development purposes, print it if twilio fails or isn't configured
        print(f"DEBUG: SMS OTP for {user.phone_number}: {otp} (Twilio failed: {e})")
        return False

def verify_otp(user, otp):
    """
    Verify the provided OTP
    """
    if not user.otp_base32:
        return False
    
    totp = pyotp.TOTP(user.otp_base32, interval=300)
    return totp.verify(otp)
