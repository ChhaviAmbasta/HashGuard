# HashGuard Dashboard

HashGuard is a Secure File Integrity Monitoring System developed using Python and Tkinter.

The system uses SHA-256 hashing to verify file integrity and detect tampered or modified files.

---

## Features

- Secure Login Authentication
- File Upload System
- SHA-256 Hash Generation
- File Integrity Verification
- Tampered File Detection
- Status Tracking (Verified / Tampered)
- Open Uploaded Files
- Delete Files
- Search Functionality
- Export PDF Reports
- Modern Dashboard UI
- Responsive Table Layout
- Color-based Verification Status

---

## Technologies Used

- Python
- Tkinter
- SQLite3
- hashlib
- ReportLab
- Pillow (PIL)

---

## Project Structure

```bash
HASHGUARD/
│
├── assets/
├── database/
├── gui/
├── uploads/
├── main.py
├── requirements.txt
└── README.md
```

---

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the project:

```bash
python gui/login.py
```

---

## Dashboard Functionalities

### Upload File
Users can upload files securely into the system.

### Verify File
Checks whether the uploaded file has been modified or tampered using SHA-256 hash comparison.

### Delete File
Removes selected files from the system.

### Export Report
Generates PDF reports containing uploaded file records.

### Open File
Allows users to directly open uploaded files from the dashboard.

### Search Feature
Search uploaded files instantly.

---

## Security Features

- SHA-256 Cryptographic Hashing
- File Integrity Monitoring
- Tampered File Detection
- Secure Local Database Storage

---

## Future Enhancements

- Real-time File Monitoring
- Email Alerts
- Cloud Storage Support
- Multi-user Authentication
- AI-based Threat Detection
- Dark/Light Mode

---

## Developed By

Chhavi Ambasta

---

## Project Type

DRDO Internship Project
