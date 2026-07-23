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
Agvisely-Early-Warning-AI/
├── app/                    # FastAPI backend
├── frontend/               # React + Vite UI
├── tests/                  # pytest (used by CI)
├── .github/workflows/      # GitHub Actions CI/CD
│   ├── ci.yml
│   └── deploy.yml
├── Dockerfile              # Backend image
├── docker-compose.yml
├── requirements.txt
├── .env.example
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
uvicorn app.main:app --reload --port 9603
```

API: http://127.0.0.1:9603  
Docs: http://127.0.0.1:9603/docs

### 5. Run frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:9604

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
curl -X POST http://127.0.0.1:9603/calls/ \
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

## CI/CD (GitHub Actions)

This repo includes a full GitHub Actions setup for **Python FastAPI** + **React (Vite)** frontend.

| Port | Service |
|------|---------|
| **9603** | Backend (FastAPI) |
| **9604** | Frontend (Vite / nginx) |

| Workflow | File | When it runs | What it does |
|----------|------|--------------|--------------|
| **CI** | `.github/workflows/ci.yml` | Push / PR to `main`, `master`, `develop` | Backend: Postgres service, install deps, Ruff lint, pytest. Frontend: `npm ci` + `npm run build` |
| **Deploy** | `.github/workflows/deploy.yml` | After CI succeeds on `main`/`master`, or manual **Run workflow** | Build Docker images and push to **GitHub Container Registry** (`ghcr.io`) |

### Full process: enable CI/CD on GitHub

#### 1. Commit & push (from your machine)

```bash
git add .
git commit -m "Add GitHub Actions CI/CD and set ports 9603/9604"
git push -u origin main
```

Repo: https://github.com/Rrevinr-Ai/Agvisely-Early-Warning-AI

#### 2. Allow Actions (first time only)

1. Open the repo on GitHub.
2. Click **Actions**.
3. If you see “Workflows aren’t enabled…”, click **I understand my workflows, go ahead and enable them**.
4. Confirm the **CI** and **Deploy** workflows appear under **All workflows**.

#### 3. CI on every push / PR

- Any push to `main`, `master`, or `develop` starts **CI**.
- Any pull request targeting those branches also starts **CI**.
- Open **Actions** → select the latest **CI** run to watch logs (backend tests + frontend build).
- A green check on the commit means CI passed.

#### 4. Deploy after CI succeeds

- When **CI** finishes successfully on a **push** to `main`/`master`, **Deploy** starts automatically.
- It builds and pushes:
  - `ghcr.io/rrevinr-ai/agvisely-early-warning-ai-backend:latest`
  - `ghcr.io/rrevinr-ai/agvisely-early-warning-ai-frontend:latest`
- To run Deploy manually: **Actions** → **Deploy** → **Run workflow** → **Run workflow**.

#### 5. Packages (Docker images)

1. Repo → **Packages** (or https://github.com/orgs/Rrevinr-Ai/packages — or your user Packages tab).
2. Or: https://github.com/Rrevinr-Ai?tab=packages
3. Make a package public (optional): package → **Package settings** → **Change visibility**.

#### 6. Run the same stack locally with Docker

```bash
cp .env.example .env
# edit .env — set OPENAI_API_KEY and other secrets

docker compose up --build
```

- Backend: http://127.0.0.1:9603  
- Frontend: http://127.0.0.1:9604  
- API docs: http://127.0.0.1:9603/docs  

#### 7. Deploy to your VPS (full process)

Files live in `deploy/`:

| File | On VPS |
|------|--------|
| `deploy/docker-compose.yml` | `/opt/agvisely/docker-compose.yml` |
| `deploy/.env.example` | `/opt/agvisely/.env` (edit secrets) |

##### A. Prepare the server (once)

```bash
ssh YOUR_USER@YOUR_VPS_IP
sudo mkdir -p /opt/agvisely
sudo chown $USER:$USER /opt/agvisely
```

From your laptop:

```bash
scp deploy/docker-compose.yml YOUR_USER@YOUR_VPS_IP:/opt/agvisely/docker-compose.yml
scp deploy/.env.example YOUR_USER@YOUR_VPS_IP:/opt/agvisely/.env
```

On the VPS:

```bash
nano /opt/agvisely/.env
# set POSTGRES_PASSWORD, OPENAI_API_KEY, PUBLIC_BASE_URL=http://YOUR_VPS_IP:9603

# Install Docker if needed: https://docs.docker.com/engine/install/
sudo ufw allow 9603/tcp
sudo ufw allow 9604/tcp
sudo ufw allow OpenSSH
```

##### B. First pull & start

Create a GitHub PAT with `read:packages`, then on the VPS:

```bash
echo YOUR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
cd /opt/agvisely
docker compose pull
docker compose up -d
```

- Backend: `http://YOUR_VPS_IP:9603`
- Frontend: `http://YOUR_VPS_IP:9604`
- Docs: `http://YOUR_VPS_IP:9603/docs`

##### C. SSH key for GitHub Actions

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f agvisely-deploy -N ""
ssh-copy-id -i agvisely-deploy.pub YOUR_USER@YOUR_VPS_IP
```

##### D. GitHub Secrets & variable

Repo → **Settings** → **Secrets and variables** → **Actions**

**Secrets**

| Name | Value |
|------|--------|
| `DEPLOY_HOST` | VPS IP or hostname |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | Full private key file `agvisely-deploy` |
| `GHCR_USERNAME` | GitHub username |
| `GHCR_TOKEN` | PAT with `read:packages` |

**Variables** tab:

| Name | Value |
|------|--------|
| `ENABLE_VPS_DEPLOY` | `true` |

##### E. Auto-deploy

Push to `main` → CI → Deploy (build images) → **Deploy to VPS** (`docker compose pull && up -d`).

Or: **Actions** → **Deploy** → **Run workflow**.

##### F. Server commands

```bash
cd /opt/agvisely
docker compose ps
docker compose logs -f backend
docker compose restart
```

---

## License

Pilot project for CIMMYT Agvisely 2.0 — see `project_details.txt` for scope.
