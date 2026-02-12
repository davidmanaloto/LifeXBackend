from django.core.management.base import BaseCommand
from blockchain.models import MedicalRecord, AuditLog
from blockchain.encryption import encryption_manager

class Command(BaseCommand):
    help = 'Encrypts existing medical records that are stored in plain text'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting encryption backfill process...'))

        # 1. Encrypt Medical Records
        records = MedicalRecord.objects.filter(is_encrypted=False)
        record_count = records.count()
        
        if record_count == 0:
            self.stdout.write('No unencrypted medical records found.')
        else:
            self.stdout.write(f'Found {record_count} unencrypted records. Encrypting...')
            for record in records:
                # Encrypt description
                if record.description and not record.description.startswith('gAAAAA'):
                    record.description = encryption_manager.encrypt(record.description)
                
                # Encrypt department
                if record.department and not record.department.startswith('gAAAAA'):
                    record.department = encryption_manager.encrypt(record.department)
                
                record.is_encrypted = True
                record.save()
                self.stdout.write(f'  - Encrypted record ID {record.id}: {record.title}')

        # 2. Update Audit Logs (optional but good for consistency)
        logs = AuditLog.objects.filter(is_encrypted=False, action='UPLOAD_RECORD')
        log_count = logs.count()
        if log_count > 0:
            self.stdout.write(f'Updating {log_count} audit logs...')
            logs.update(is_encrypted=True)

        self.stdout.write(self.style.SUCCESS(f'Successfully backfilled encryption for {record_count} records.'))
