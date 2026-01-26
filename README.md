# LifeX - Blockchain Medical Record Management System

LifeX is a secure, decentralized platform for managing medical records using blockchain technology. It ensures data integrity and provides a transparent audit trail for all medical activities.

## 🚀 How to Run the Project

### 1. Prerequisites
Ensure you have the following installed:
- **Python 3.10+**
- **Node.js & npm**
- **Ganache** (CLI or GUI)
- **Truffle** (`npm install -g truffle`)

### 2. Blockchain Setup
1. Start Ganache on port `7545`:
   ```bash
   ganache --port 7545
   ```
2. Navigate to the blockchain directory and deploy the smart contracts:
   ```bash
   cd lifex/blockchain_project
   truffle compile
   truffle migrate --reset
   ```

### 3. Backend Setup
1. Create and activate a virtual environment:
   ```bash
   # From the project root
   python -m venv venv
   .\venv\Scripts\Activate.ps1 # Windows
   ```
2. Install dependencies:
   ```bash
   cd lifex
   pip install -r requirements.txt
   ```
3. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

### 4. Access the Platform
- **Staff Dashboard**: `http://127.0.0.1:8000/staff/`
- **Patient Portal**: `http://127.0.0.1:8000/patient/`
- **Admin Dashboard**: `http://127.0.0.1:8000/dashboard/`

---

## ⛓️ How Blockchain Works in LifeX

LifeX uses private blockchain technology (Ethereum via Ganache) to secure medical records. Unlike traditional databases where records can be silently edited, LifeX provides a cryptographic guarantee of authenticity.

### 1. Cryptographic Document Hashing
When a Nurse uploads a medical record (PDF or Image), the system immediately generates a **SHA-256 Hash**. 
- Think of this hash as a "Digital Fingerprint."
- Even a tiny change in the file (like changing one letter) would result in a completely different fingerprint.

### 2. Smart Contract Registry
Instead of storing the entire file on the blockchain (which is expensive and slow), LifeX stores:
- **Document ID**: A unique reference.
- **Document Hash**: The "Fingerprint."
- **Owner Address**: The cryptographic identity of the patient.

This data is written to the **DocumentRegistry** smart contract. Once stored, it is **immutable**—it can never be changed or deleted.

### 3. Verification Protocol
When a Patient or Doctor views a record:
1. The system fetches the original file from the server.
2. It re-calculates the hash of that file in real-time.
3. It compares this "New Hash" with the "On-Chain Hash" stored in Ganache.
4. If they match, a green **"✓ Verified on Blockchain"** badge appears, proving the file has not been tampered with since its creation.

### 4. Role-Based Permissions
- **Nurses**: Authorized to register new records onto the blockchain.
- **Doctors**: Authorized to view verified records and verify them on-chain.
- **Patients**: Can view their own verified history and prove ownership of their data.
- **Receptionists**: Manage the administrative flow leading up to medical documentation.

---
*Built with Django, Web3.py, and Solidity.*
