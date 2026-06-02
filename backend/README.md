# CareerPilot AI Backend Service

Modular, production-ready asynchronous Python API built using **FastAPI**, **Pydantic v2**, and **Motor (MongoDB Async Driver)**.

---

## 🛠️ Architecture Overview

- **FastAPI Engine**: Asynchronous ASGI server running on Uvicorn.
- **Pydantic v2 Validation**: Strict typing guards on all request payloads and JSON structures.
- **Motor Client Database**: Connection broker targeting MongoDB Atlas with graceful fallback to local instances.
- **Unified Middleware Logging**: Console request trackers profiling routing coordinates and IP tags.
- **Global Error Protection**: Exception interceptors securing server trace logs.

---

## 🚀 Setup & Execution

### 1. Ingest Dependencies
Ensure Python 3.9+ is installed, create a virtual environment, and install dependencies:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configurations
Configure your database Atlas strings safely via environment variables or a local `.env` template:
```env
PORT=8000
MONGODB_URL=mongodb+srv://<username>:<password>@cluster0.mongodb.net/careerpilot?retryWrites=true&w=majority
CORS_ORIGINS=http://localhost:3000,http://localhost:3000
```

### 3. Server Startup
Launch the development server via:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Exposes documentation portals at:
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Telemetry**: `http://localhost:8000/redoc`
