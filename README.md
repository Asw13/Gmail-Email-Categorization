# Gmail Email Categorization & No-Reply Cleanup (Gmail API)

A production-grade Python application that analyzes Gmail inbox data and safely cleans automated emails using the official Gmail API, OAuth 2.0 authentication, batch processing, and robust rate-limit handling.

---

## 📌 Project Overview

This project connects securely to a Gmail account and performs two main tasks:

1. **Email Sender Analysis**
   - Identifies which senders send the most emails
   - Generates a sender-wise frequency report

2. **Automated Email Cleanup**
   - Detects automated emails (`noreply`, `no-reply`, `no_reply`)
   - Safely moves selected emails to Gmail Trash
   - Logs each deleted email for auditing and recovery

The system is designed to respect Gmail API quotas and includes retry logic, exponential backoff, and hard stop conditions.

---

## 🚀 Key Features

- OAuth 2.0 authentication (no password storage)
- Gmail API read and modify operations
- Batch processing for performance
- Sender frequency analysis using Python `Counter`
- Controlled deletion with:
  - Retry limits per email
  - Consecutive failure break logic
  - Rate-limit aware backoff
- Audit log of deleted emails
- Safe deletion (emails moved to Trash, recoverable for 30 days)

---

## 🧠 Why This Project Matters

This project demonstrates **real-world API engineering**, including:

- Handling third-party API rate limits
- Defensive programming with retries and backoff
- Batch request optimization
- Safe automation design
- Production-ready logging and error handling

These patterns are commonly used in backend and integration systems.

---

## 🛠️ Technologies Used

- Python 3
- Gmail API
- Google OAuth 2.0
- google-api-python-client
- google-auth
- google-auth-oauthlib

---

## 📂 Project Structure
  - Gmail-Email-Categorization/
│
├── gmail_sender_analysis.py # Main application logic
├── README.md # Documentation
├── requirements.txt # Dependencies
├── .gitignore # Security and hygiene

