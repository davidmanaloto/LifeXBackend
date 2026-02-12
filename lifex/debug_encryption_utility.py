import os
import sys
import django
from cryptography.fernet import Fernet

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifex.settings')
django.setup()

from blockchain.encryption import encryption_manager

def test_encryption():
    print("--- LifeX Encryption/Decryption Debugging Script ---")
    
    # 1. Check if ENCRYPTION_KEY is set
    from django.conf import settings
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        print("[WARNING] ENCRYPTION_KEY is not set in .env. Using fallback key derived from SECRET_KEY.")
        # Generate a suggested key for the user
        suggested_key = Fernet.generate_key().decode()
        print(f"[ACTION REQUIRED] Please add the following to your .env file for production use:")
        print(f"ENCRYPTION_KEY={suggested_key}")
    else:
        print(f"[INFO] Using ENCRYPTION_KEY from settings.")

    # 2. Test simple string encryption
    test_data = "Patient: John Doe, Diagnosis: Hypertension, Date: 2026-02-12"
    print(f"\n[TEST 1] Original Data: {test_data}")
    
    encrypted = encryption_manager.encrypt(test_data)
    print(f"[TEST 1] Encrypted Data: {encrypted}")
    
    decrypted = encryption_manager.decrypt(encrypted)
    print(f"[TEST 1] Decrypted Data: {decrypted}")
    
    if test_data == decrypted:
        print("[SUCCESS] Encryption and Decryption match!")
    else:
        print("[FAILURE] Decrypted data does not match original!")

    # 3. Test multi-line data
    multi_line_data = """
    Medical Report
    --------------
    Patient ID: P-12345
    Blood Type: O+
    Allergies: Penicillin
    Notes: Patient presents with mild symptoms of flu.
    """
    print(f"\n[TEST 2] Testing multi-line medical report...")
    enc_multi = encryption_manager.encrypt(multi_line_data)
    dec_multi = encryption_manager.decrypt(enc_multi)
    
    if multi_line_data == dec_multi:
        print("[SUCCESS] Multi-line data encryption/decryption works!")
    else:
        print("[FAILURE] Multi-line data mismatch!")

    # 4. Test Model-level encryption (without saving to DB)
    print("\n[TEST 3] Testing MedicalRecord model-level encryption...")
    from blockchain.models import MedicalRecord
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Create a mock patient
    patient = User(email="test_patient@example.com", role="PATIENT")
    
    record = MedicalRecord(
        patient=patient,
        title="Physical Exam",
        description="Patient is in good health.",
        department="General Medicine",
        date_of_service="2026-02-12"
    )
    
    orig_desc = record.description
    orig_dept = record.department
    
    print(f"Original Description: {orig_desc}")
    print(f"Original Department: {orig_dept}")
    
    record.encrypt_sensitive_fields()
    
    print(f"Encrypted Description: {record.description}")
    print(f"Encrypted Department: {record.department}")
    
    dec_desc = record.get_decrypted_description()
    dec_dept = record.get_decrypted_department()
    
    print(f"Decrypted Description: {dec_desc}")
    print(f"Decrypted Department: {dec_dept}")
    
    if dec_desc == orig_desc and dec_dept == orig_dept:
        print("[SUCCESS] Model-level encryption/decryption works!")
    else:
        print("[FAILURE] Model-level mismatch!")

    # 5. Test Audit Log encryption tracking
    print("\n[TEST 4] Testing AuditLog encryption status tracking...")
    from blockchain.models import AuditLog
    from blockchain.medical_views import log_action
    
    # Create a mock staff user
    staff_user = User.objects.filter(role__in=['NURSE', 'ADMIN']).first()
    if not staff_user:
        staff_user = User.objects.create_user(email="mock_staff@example.com", password="password123", role="ADMIN")
    
    log_action(
        user=staff_user,
        action='UPLOAD_RECORD',
        resource_type='MEDICAL_RECORD',
        resource_id='test-123',
        details='Testing encryption log entry',
        is_encrypted=True
    )
    
    last_log = AuditLog.objects.order_by('-created_at').first()
    print(f"Audit Log ID: {last_log.id}")
    print(f"Action: {last_log.action}")
    print(f"Is Encrypted: {last_log.is_encrypted}")
    
    if last_log.is_encrypted:
        print("[SUCCESS] AuditLog correctly tracked encryption status!")
    else:
        print("[FAILURE] AuditLog failed to track encryption status!")

if __name__ == "__main__":
    test_encryption()
