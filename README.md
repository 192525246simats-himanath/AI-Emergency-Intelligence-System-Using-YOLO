# AI-Based Emergency Intelligence and Response System Using YOLO

**Senior Capstone Project**  
**Course:** CSA1713 - Artificial Intelligence (Review 2)  
**Institution:** Saveetha University (SIMATS)  
**Project Guide:** Dr. Sundar Rajan S.  

### Project Contributors
- **M. Himanath Sai** (Reg: 192525246)
- **P. Arjun** (Reg: 192524194)
- **K. Lohith Kumar** (Reg: 192511155)
- **K. Sampath** (Reg: 192572006)

---

## 📌 Project Overview
The **AI-Based Emergency Intelligence and Response System** is a real-time computer vision and emergency management platform. It ingests live traffic CCTV footage, recorded surveillance videos, or uploaded incident photos, performs multi-class object detection using **YOLOv8**, and evaluates spatial proximity and Intersection over Union (IoU) overlap to estimate potential vehicle collision hazards. 

When high-risk proximity is identified, the system generates visual warning overlays, logs timestamped incidents to an SQLite database, and enables control-room operators to trigger simulated emergency dispatch signals to traffic and medical responders.

> **Ethical & Safety Notice:** In compliance with academic standards, all collision indicators are classified as *estimated collision risks* based on 2D camera geometry and are intended for human operator verification. All emergency dispatch actions are strictly *simulated*.

---

## 🏛️ Architecture & Deployment Strategy

```
               +----------------------------------------------------+
               |                Client Web Browser                  |
               |       (Emergency Operations Control Centre)        |
               +-------------------------+--------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
         [ Static CDN / UI ]                     [ REST API & Stream ]
       +--------------------+                  +-----------------------+
       |   Vercel Hosting   |                  |    Render Hosting     |
       |  (frontend/ folder)|                  |   (backend/ folder)   |
       +--------------------+                  +-----------------------+
       | • index.html       |                  | • Flask 3.x WSGI App  |
       | • css/style.css    |                  | • YOLOv8 Nano Engine  |
       | • js/api.js        |                  | • OpenCV Video Stream |
       | • js/app.js        |                  | • Gunicorn Server     |
       | • vercel.json      |                  | • SQLite Database     |
       +--------------------+                  +-----------------------+
```

---

## 🚀 Local Development Setup (Windows)

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11 / 3.15)
- Web browser (Chrome, Edge, or Firefox)

### 2. Backend Setup
```powershell
# Navigate to the backend directory
cd backend

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run automated backend test suite (verifies all 10 endpoints)
python test_backend.py

# Start local Flask development server (Port 5000)
python app.py
```
Backend will be available at: `http://localhost:5000`  
Health check endpoint: `http://localhost:5000/api/health`

### 3. Frontend Setup
You can serve the `frontend/` folder with any static web server:
```powershell
# In a separate terminal, from the project root:
cd frontend
python -m http.server 3000
```
Open `http://localhost:3000` in your web browser.  
By default, the frontend automatically connects to `http://localhost:5000`. You can change the backend URL at any time via the **Settings (⚙️)** button in the top navigation bar.

---

## ☁️ Cloud Deployment Guide

### A. Deploy Backend on Render (Web Service)
1. Push your repository to **GitHub**:
   ```powershell
   git init
   git add .
   git commit -m "Initial commit of Emergency Intelligence and Response System"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. Log in to [Render](https://render.com).
3. Click **New +** > **Web Service**.
4. Connect your GitHub repository.
5. Configure the service settings:
   - **Name:** `emergency-intelligence-backend`
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Region:** Choose closest to you (e.g., Oregon or Frankfurt)
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 app:app`
   - **Plan:** Free
6. Add Environment Variables:
   - `PORT`: `10000`
   - `CORS_ALLOWED_ORIGINS`: `*`
   - `FLASK_DEBUG`: `0`
7. Click **Create Web Service**. Once deployed, Render will provide a public URL (e.g., `https://emergency-intelligence-backend.onrender.com`).

---

### B. Deploy Frontend on Vercel
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** > **Project**.
3. Import your GitHub repository.
4. In the configuration screen:
   - **Framework Preset:** `Other`
   - **Root Directory:** Click *Edit* and select **`frontend`** *(CRITICAL: This ensures Vercel only deploys the frontend and does not bundle Python AI dependencies).*
5. Click **Deploy**.
6. Once deployed, open your live Vercel URL.
7. Click the **Settings (⚙️)** button in the top right of your EOCC Dashboard, paste your **Render Backend URL**, and click **Save URL**.
8. Your full-stack cloud system is now live!

---

## 📋 Capstone Review Checklist
- [x] Module 1: Video Processing (OpenCV stream reader & frame extraction)
- [x] Module 2: Object Detection (YOLOv8 multi-class vehicle & pedestrian classification)
- [x] Module 3: Accident Analysis (Spatial IoU overlaps & centroid proximity heuristics)
- [x] Module 4: Alert & Response (Real-time telemetry, incident database, and simulated dispatch)
- [x] Automated Test Suite: 10/10 endpoints verified
- [x] Vercel + Render Decoupled Architecture
