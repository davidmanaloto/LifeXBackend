# LifeX Data Encryption Guide

This document explains the encryption and decryption system implemented in LifeX to protect sensitive patient information.

## 🔒 Overview

While the blockchain ensures **integrity** (that data hasn't been tampered with), the Encryption System ensure **confidentiality** (that data cannot be read by unauthorized parties, even if they have database access).

We use **Field-Level Encryption** for sensitive textual data within medical records.

## 🛠️ Technology Stack

- **Library**: `cryptography` (Python)
- **Algorithm**: **Fernet (AES-128 in CBC mode)**
- **Authentication**: HMAC with SHA256
- **Key Derivation**: 32-byte URL-safe base64-encoded key

## 🔑 Configuration

Encryption is managed via the `ENCRYPTION_KEY` environment variable.

1.  **Generate a Key**:
    ```powershell
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
2.  **Add to `.env`**:
    ```env
    ENCRYPTION_KEY=your-generated-key-here
    ```

> ⚠️ **CRITICAL**: If the `ENCRYPTION_KEY` is lost or changed, all previously encrypted data will become unreadable. Keep a secure backup of this key.

## 📁 Implementation Details

### 1. The Encryption Utility (`lifex/blockchain/encryption.py`)
A singleton `encryption_manager` provides high-level `encrypt(data)` and `decrypt(data)` methods.

### 2. Model Integration (`lifex/blockchain/models.py`)
The `MedicalRecord` model includes helper methods to handle encryption logic:
- `encrypt_sensitive_fields()`: Encrypts fields like `description` and `department`.
- `get_decrypted_description()`: Safely returns the plain-text description.
- `get_decrypted_department()`: Safely returns the plain-text department name.

### 3. API Automation (`lifex/blockchain/medical_serializers.py`)
Encryption and decryption are handled automatically at the API layer:
- **Upload**: `MedicalRecordUploadSerializer` encrypts sensitive fields before saving to the database.
- **View**: `MedicalRecordSerializer` decrypts fields in the `to_representation` method before sending them to the frontend.

## 🕵️ Traceability & Auditing

Admin users can monitor the encryption status of the system through:

1.  **Audit Logs**: Each `UPLOAD_RECORD` action now includes an `is_encrypted` flag.
2.  **System Statistics**: The Admin Dashboard's system stats API returns an `encrypted` count under `medical_records`.
3.  **Database Visibility**: The `MedicalRecord` table contains an `is_encrypted` boolean to verify each record's state at a glance.

## 🧪 Testing & Debugging

A dedicated debugging script is provided to verify the system:

```powershell
python debug_encryption_utility.py
```

This script tests:
1.  **Config Check**: Verifies if `ENCRYPTION_KEY` is correctly loaded.
2.  **Unit Test**: Encrypts and decrypts a sample string to verify the algorithm.
3.  **Model Test**: Simulates a `MedicalRecord` object to verify model-level logic.

## 🔍 Searchability Note
Note that encrypted fields are **not searchable** using standard SQL `LIKE` queries because the encrypted text changes every time (even for the same input) due to unique Initialization Vectors (IVs). Fields like `title` are kept in plain text to allow for basic searching.
