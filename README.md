MeetingIQ — AI-Powered Meeting Intelligence Platform

  Transform audio recordings, YouTube videos and text into
  actionable AI insights.

  ## Features
  - 4 Input Types: Audio/Video, YouTube URL, PDF/DOCX, Raw Text
  - 8 AI Agents running in a LangGraph pipeline
  - 2 Analysis Modes: Meeting Analysis & Content Analysis
  - Export to TXT, DOCX, PDF, Excel
  - Real-time progress tracking via Server-Sent Events

  ## Tech Stack
  - **AI/LLM:** AWS Bedrock (Amazon Nova Pro)
  - **Transcription:** AWS Transcribe
  - **Agents:** LangGraph
  - **Backend:** FastAPI (Python)
  - **Frontend:** Angular 19 + Angular Material
  - **Storage:** Amazon S3

  ## Setup

  ### Backend
  ```bash
  cd backend
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  cp .env.example .env        # Fill in your AWS credentials
  uvicorn main:app --reload --port 8000

  Frontend

  cd frontend
  npm install
  npm start

  Open http://localhost:4200

  4. Click **Commit changes**

  ---

  ### Step 7 — Add Topics (makes it discoverable)

  1. On your repo page, click the **⚙️ gear icon** next to
  "About"
  2. In the **Topics** field add:
  aws-bedrock  langgraph  angular  fastapi  multi-agent  rag
  python  ai
  3. Click **Save changes**

  ---

  ### Step 8 — Restore deleted files on your PC

  After uploading, restore what you deleted so your app still
  works locally:

  ```bash
  # Restore backend dependencies
  cd C:\Projects\meeting-intelligence\backend
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt

  # Restore your .env (rename .env.backup back to .env)

  # Restore frontend dependencies
  cd C:\Projects\meeting-intelligence\frontend
  npm install

  ---
  Final Result

  Your repo will be live at:
  https://github.com/YOUR_USERNAME/meeting-intelligence

  Share this link with recruiters. The repo will show the full
  code, README with tech stack, and all agent/pipeline files.
