
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

1️⃣ Clone

git clone https://github.com/dhsaipriya25/meeting-intelligence.git

cd meeting-intelligence


2️⃣ Backend

cd backend

python -m venv venv

# Windows: venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # add your AWS credentials

uvicorn main:app --reload --port 8000


3️⃣ Frontend

cd frontend

npm install

npm start

Open http://localhost:4200

🔐 Environment Variables
Variable	Description
AWS_ACCESS_KEY_ID	AWS access key
AWS_SECRET_ACCESS_KEY	AWS secret key
AWS_REGION	e.g. us-east-1
S3_BUCKET_NAME	Bucket for uploads.
