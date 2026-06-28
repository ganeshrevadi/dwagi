# DWAGI — Telegram Spending Bot + Job Tracker

Personal spending analysis bot for Telegram, now with an automated job tracker. Fetches real bank transactions via India's Account Aggregator (Setu), imports credit card PDF statements, answers spending questions with Gemini, and monitors job openings at companies with 500+ employees.

## Features

### Spending
- **Bank accounts** — consent-based fetch via Setu Account Aggregator (`/connect`)
- **Credit card** — upload e-statement PDF in Telegram chat
- **Spending chat** — natural language questions powered by Gemini + structured DB queries
- **Unified view** — all accounts in one transaction store

### Job Tracker
- **Multi-source scraping** — Google Jobs (aggregator), Greenhouse, Lever, RemoteOK, and LinkedIn
- **Company filter** — only jobs at companies with 500+ employees (100+ companies pre-curated)
- **Profile matching** — scores jobs against your skills, target titles, locations, and salary
- **Referral suggestions** — flags jobs at competitive companies where a referral would help
- **Application pipeline** — tracks discovered → applied → interviewing → offer status
- **Twice-daily scans** — automatic morning (8 AM) and evening (6 PM) job digests via Telegram

## Quick start (local)

### 1. Prerequisites

- Python 3.11+
- PostgreSQL (or [Neon](https://neon.tech) free tier)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- [Gemini API key](https://aistudio.google.com/apikey) (free)
- [Setu Bridge](https://bridge.setu.co/) sandbox credentials (for bank linking)

### 2. Setup

```bash
cd puppy
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens
```

### 3. Run

```bash
uvicorn app.main:app --reload --port 8000
```

For local Telegram webhooks, expose with ngrok:

```bash
ngrok http 8000
# Set PUBLIC_BASE_URL=https://xxxx.ngrok-free.app in .env
# Restart server — webhook registers on startup
```

### 4. Telegram commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome |
| `/connect 9876543210` | Link bank accounts via Account Aggregator |
| `/upload` | Instructions for credit card PDF |
| `/status` | Transaction count and consent status |
| `/sync` | Manually refresh bank transactions |
| `/jobs` | Today's matching jobs |
| `/jobs:all` | All tracked jobs |
| `/apply <id>` | Mark a job as applied |
| `/referrals` | Jobs where a referral would help |
| `/pipeline` | Application summary |
| `/scan` | Run job search now |
| `/profile` | Show your search profile |
| Send PDF | Import credit card statement |
| Any text | Ask spending questions |

## Deploy to Render (free)

1. Push this repo to GitHub
2. Create a [Neon](https://neon.tech) Postgres database → copy `DATABASE_URL`
3. [Render](https://render.com) → New Web Service → connect repo → use Dockerfile
4. Set environment variables from `.env.example`
5. Set `PUBLIC_BASE_URL` to your Render URL (e.g. `https://puppy.onrender.com`)
6. [cron-job.org](https://cron-job.org) — ping `GET /health` every 14 min (keeps free tier awake)
7. Optional: schedule `POST /sync` weekly for bank refresh
8. Schedule `POST /jobs/scan` twice daily (8 AM, 6 PM) for automatic job scans

## Setu Account Aggregator setup

### Sandbox (development)

1. Register at [Setu Bridge](https://bridge.setu.co/)
2. Create FIU → Account Aggregator product
3. Set notification URL: `{PUBLIC_BASE_URL}/setu/webhook`
4. Copy `client_id`, `client_secret`, `product_instance_id` to `.env`
5. Test with `/connect <your-10-digit-mobile>`

### Production (real bank data)

1. Complete KYC on Setu Bridge (Step 4–5)
2. Set `SETU_ENV=production` and production `SETU_BASE_URL` from Setu
3. Link your bank accounts in the AA consent flow
4. Expect ~₹10–25 per successful data fetch

## Environment variables

See [`.env.example`](.env.example) for the full list.

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From BotFather |
| `TELEGRAM_SECRET_TOKEN` | Yes | Random string for webhook security |
| `ALLOWED_TELEGRAM_USER_IDS` | Recommended | Your Telegram user ID (comma-separated) |
| `DATABASE_URL` | Yes | Postgres connection string |
| `PUBLIC_BASE_URL` | Yes | Public HTTPS URL of this app |
| `GEMINI_API_KEY` | Yes | For spending chat |
| `SETU_CLIENT_ID` | For banks | Setu Bridge credentials |
| `SETU_CLIENT_SECRET` | For banks | Setu Bridge credentials |
| `SETU_PRODUCT_INSTANCE_ID` | For banks | Setu product ID |
| `JOB_SCAN_ENABLED` | No | Enable job tracker (default: true) |
| `COMPANY_MIN_EMPLOYEES` | No | Minimum company size to track (default: 500) |
| `GOOGLE_JOBS_ENABLED` | No | Enable Google Jobs scraper |
| `GREENHOUSE_ENABLED` | No | Enable Greenhouse API scraper |
| `LEVER_ENABLED` | No | Enable Lever API scraper |
| `REMOTEOK_ENABLED` | No | Enable RemoteOK scraper |
| `LINKEDIN_ENABLED` | No | Enable LinkedIn scraper (may need rotation) |
| `PROFILE_SKILLS` | No | Comma-separated skills for job matching |
| `PROFILE_TARGET_TITLES` | No | Comma-separated target job titles |
| `PROFILE_LOCATIONS` | No | Comma-separated preferred locations |
| `PROFILE_MIN_SALARY` | No | Minimum salary threshold |

Find your Telegram user ID: message [@userinfobot](https://t.me/userinfobot).

## Architecture

```
Telegram → FastAPI webhook → Postgres
                ↓
         Setu AA (banks) + PDF parser (credit card)
                ↓
         Gemini (tool-calling over transactions)
                ↓
         Job Scrapers (Google Jobs, Greenhouse, Lever, RemoteOK, LinkedIn)
                ↓
         Matcher (profile scoring + company size filter)
                ↓
         Telegram digest (morning + evening)
```

## Project structure

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings
├── db/                  # SQLAlchemy models
├── telegram/            # Bot client + handlers
├── banking/             # Setu AA integration
├── statements/          # Credit card PDF parser
├── chat/                # Gemini agent + query tools
├── jobs/                # Job tracker module
│   ├── models.py        # Job, JobApplication, Company tables
│   ├── company_db.py    # Curated companies with employee counts
│   ├── matcher.py       # Profile-based job scoring
│   ├── scanner.py       # Orchestrator (run scrapers → match → store)
│   ├── telegram_commands.py  # Telegram command handlers
│   ├── router.py        # HTTP endpoints
│   ├── config.py        # Job-specific settings
│   └── scrapers/
│       ├── google_jobs.py   # Google Jobs scraper
│       ├── greenhouse.py    # Greenhouse API scraper
│       ├── lever.py         # Lever API scraper
│       ├── remoteok.py      # RemoteOK API scraper
│       └── linkedin.py      # LinkedIn scraper
└── routers/             # HTTP endpoints
```

## License

Private / personal use.
