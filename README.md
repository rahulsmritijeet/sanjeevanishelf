# Sanjeevani Shelf v1.1 - Godown Management System

## Overview

**Sanjeevani Shelf** is an industrial-grade, offline-first crop storage management system designed for rural panchayats in India. It manages inventory, quality control, billing, and farmer payments with full RFID tracking, moisture monitoring, and WhatsApp notifications.

### Key Features

- **3-Arduino Hardware**: RFID (RC522), Weight (HX711), Moisture (4 sensors) via HC-05 Bluetooth
- **Multi-language**: English, Hindi, Bengali UI and notifications
- **Offline-first**: Local SQLite database with WAL mode
- **Payment Simulation**: Razorpay QR + simulation buttons (no real money)
- **WhatsApp Integration**: Queue-based notifications with retry
- **Session Management**: Full rollback/recovery on power failure
- **Quality Control**: Moisture validation, grading, expiry management
- **FIFO Inventory**: Capacity checks, stack allocation, confiscation

---

## Quick Start (Simulation Mode)

### Prerequisites

- Raspberry Pi 3B+ or better (or any Linux PC for development)
- Python 3.11+
- 16GB+ SD card

### Installation

```bash
# Clone repository
git clone <repo-url>
cd sanjeevani_shelf

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
simulate this on windows too gng

```bash
# 1. Clone the repository
git clone <repo-url>
cd sanjeevani_shelf

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Initialize database
python -c "from database.migrations import apply_migrations; apply_migrations()"

# 6. Run the application
python ui/app.py

