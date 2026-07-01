# Agvisely Service Agent

![কৃষি সহায়তা এজেন্ট](krishi.png)

Bangla voice-based AI farming advisory system for Bangladeshi farmers — built for the CIMMYT / Agvisely platform.

Farmers can ask questions about **weather**, **crop advisories**, and **wheat disease warnings** in Bangla. The AI agent responds like a real krishi extension officer.

---

## Features

- **AI Call Agent** — multi-turn Bangla Q&A with tool calling (Agvisely + GPT backup)
- **Weather & Farming Advice** — temperature, crops to plant/harvest, urgent farm actions
- **Crop Advisory** — location-specific advice from Agvisely API
- **Wheat Disease Forecast** — pre-season static disease warnings
- **Speech** — Whisper (Bangla STT) + Edge TTS (Bangladeshi `bn-BD` voice)
- **Farmer Registry** — phone, location, preferred crop
- **Survey / Evaluation** — comprehension, trust, adoption tracking
- **React Frontend** — Bangla UI for testing all features

---

## Project Structure

```
Service_agent/
├── app/
│   ├── api/           # FastAPI routes
│   ├── models/        # SQLAlchemy models (farmer, call, survey)
│   ├── services/      # AI agent, Agvisely, GPT backup, TTS, Whisper
│   ├── prompts/       # System prompt for call agent
│   └── main.py        # FastAPI entry point
├── frontend/          # React + Vite UI
├── requirements.txt
├── .env.example       # Environment template
└── README.md
```

---

## Requirements

- Python 3.12+
- Node.js 18+
- PostgreSQL (port 5433 in this setup)
- OpenAI API key

---

## Setup

### 1. Clone & virtual environment

```bash
cd Service_agent
python -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
```

### 2. Database

Create PostgreSQL database:

```sql
CREATE DATABASE service_agent;
```

### 3. Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@localhost:5433/service_agent
OPENAI_API_KEY=sk-your-key

# Agvisely (from CIMMYT team)
AGVISELY_API_URL=https://your-agvisely-api
AGVISELY_API_KEY=your_key

# GPT backup when Agvisely is unavailable
GPT_BACKUP_ENABLED=true

# Bangladeshi Bangla voice
TTS_PROVIDER=edge
TTS_VOICE=bn-BD-PradeepNeural
```

### 4. Run backend

From project root (not inside `app/`):

```bash
uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs

### 5. Run frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/calls/` | AI agent — ask question (text or audio) |
| GET | `/calls/{id}` | Get call record |
| POST | `/farmers/` | Register / update farmer |
| GET | `/farmers/{phone}` | Get farmer by phone |
| POST | `/weather/` | Weather + farming advice |
| POST | `/advisory/` | Crop advisory from Agvisely |
| GET | `/disease/wheat` | Wheat disease forecast |
| POST | `/speech/transcribe` | Bangla audio → text |
| POST | `/speech/speak` | Bangla text → voice (mp3) |
| POST | `/surveys/` | Submit evaluation survey |

---

## Example: Ask the AI Agent

```bash
curl -X POST http://127.0.0.1:8000/calls/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "01712345678",
    "question_text": "আজকের আবহাওয়া কেমন?",
    "district": "Dhaka",
    "crop": "rice"
  }'
```

---

## Voice Options

| Setting | Value | Notes |
|---------|-------|-------|
| `TTS_PROVIDER=edge` | `bn-BD-PradeepNeural` | Bangladeshi male (recommended) |
| `TTS_PROVIDER=edge` | `bn-BD-NabanitaNeural` | Bangladeshi female |
| `TTS_PROVIDER=openai` | `nova` | Less natural for Bangla |

---

## How the AI Agent Works

1. Farmer sends a Bangla question (text or voice)
2. Agent calls tools: `get_weather`, `get_crop_advisory`, `get_wheat_disease_forecast`
3. Data fetched from **Agvisely API** (live) or **GPT backup** (general seasonal advice)
4. Agent replies in natural spoken Bangla
5. Call logged to PostgreSQL

---

## Agvisely API Credentials

Contact CIMMYT / Agvisely team for:

- API base URL
- API key
- Documentation for weather & crop endpoints

Until credentials are set, GPT backup provides general farming guidance with a disclaimer.

---

## License

Pilot project for CIMMYT Agvisely 2.0 — see `project_details.txt` for scope.
