# 🎥 Secure Video Upload and Streaming (FastAPI + Kafka + React)

This project securely uploads, encrypts, and streams videos via Apache Kafka using a FastAPI backend and React frontend.

## 🚀 Features
- Video upload with encryption (AES/Fernet)
- Kafka-based streaming system
- React frontend with progress bar and delete option
- Database (SQLite/MySQL) integration for metadata

## 🧩 Tech Stack
**Backend:** FastAPI, Kafka, Cryptography, SQLAlchemy  
**Frontend:** React (Hooks, Fetch API)  
**Database:** SQLite/MySQL  
**Containerization:** Docker + Docker Compose  

## ⚙️ How to Run
### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
