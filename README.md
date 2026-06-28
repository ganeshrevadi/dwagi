# DWAGI — Telegram Spending Bot + Job Tracker

Personal finance analysis and SWE job discovery bot for Telegram. Fetches bank transactions via India's Account Aggregator (Setu) or PDF import, answers spending questions with Gemini, and automatically discovers Software Engineering jobs at companies with 500+ employees.

## Features

### Spending
- **Bank accounts** — consent-based fetch via Setu Account Aggregator (`/connect <phone>`)
- **Credit card statements** — upload e-statement PDF, automatically parsed
- **Bank statements** — upload savings/current account PDF, automatically parsed
- **Spending chat** — ask questions in plain English ("how much did I spend on food last month?")
- **Unified view** — all sources in one transaction store, categorized automatically

### Job Tracker
- **Multi-source scraping** — Greenhouse, Ashby, LinkedIn, RemoteOK, Adzuna (opt-in)
- **Company filter** — only jobs at companies with 500+ employees (169 companies pre-curated)
- **Resume-driven profile** — upload your resume PDF, skills and target titles extracted automatically
- **Seniority filtering** — blocks Senior (4y), Staff (5y), Manager (4y) roles if your profile shows 3 YoE
- **Scoring** — ranks jobs by skills match, location, salary
- **Referral suggestions** — flags competitive companies where a referral helps
- **Pipeline tracking** — discovered → applied → interviewing → offer
- **On-demand scans** — `/scan` runs all scrapers immediately
- **Location filter** — Bangalore, Remote (work-from-India), other Indian cities

### Architecture

```
Telegram ←→ FastAPI ←→ Postgres
                ↓
         Setu AA (banks) + PDF parser (credit card + bank statement)
                ↓
         Gemini (tool-calling AI over transactions)
                ↓
         Job scrapers (Greenhouse, Ashby, LinkedIn, RemoteOK, Adzuna)
                ↓
         Matcher (resume profile + seniority + company size → scoring)
```

## Quick start

### Prerequisites
- Python 3.11+
- PostgreSQL (or [Neon](https://neon.tech) free tier)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- [Gemini API key](https://aistudio.google.com/apikey) (free tier: 20 req/day)
- [Setu Bridge](https://bridge.setu.co/) sandbox (optional, for bank linking)

### Setup

```bash
git clone https://github.com/ganeshrevadi/dwagi
cd dwagi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your tokens (see Configuration section)
```

### Run (long polling — simplest)

```bash
python scripts/run_polling.py
```

No ngrok, no webhooks. Bot responds via polling Telegram's API every 30 seconds.

### Run (webhook mode)

```bash
uvicorn app.main:app --reload --port 8000
```

Expose with ngrok for Telegram webhook + Setu callbacks:

```bash
ngrok http 8000
# Set PUBLIC_BASE_URL=https://xxxx.ngrok-free.app in .env
# Restart — webhook registers on startup
```

### Verify

Open Telegram, message your bot:

```
/start
/status
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Full command list |
| `/connect 9876543210` | Link bank accounts via Account Aggregator |
| `/upload` | Instructions for statement PDF upload |
| `/status` | Transaction count and linked accounts |
| `/sync` | Manually refresh bank transactions |
| `/scan` | Run job search now |
| `/jobs` | Today's matching jobs |
| `/jobs:all` | All tracked jobs |
| `/apply <id>` | Mark a job as applied |
| `/referrals` | Jobs needing a referral |
| `/pipeline` | Application summary |
| `/profile` | Show your search profile |
| `/resume` | Show parsed resume data |
| *Send PDF named "resume"* | Upload/update your resume |
| *Send any PDF* | Import credit card or bank statement |
| *Any text* | Ask spending questions to AI |

## Spending: import your data

### Option A: Bank statement PDF (easiest)

1. Download your bank e-statement from net banking or email
2. Send the PDF to the bot (include "statement" in filename for best results)
3. Bot parses transactions and categorizes them automatically

Supports: SBI, HDFC, ICICI, Axis, and most Indian bank PDFs.

### Option B: Credit card PDF

Same flow — send your credit card e-statement PDF. Bot auto-detects it.

### Option C: Setu Account Aggregator (automated)

Connect your bank accounts for automatic transaction fetching:

```
/connect 9876543210
```

You'll receive a consent link. Approve it via your bank's AA app to grant read-only access.

**Pricing**: Sandbox is free. Production costs ~₹10–25 per successful data fetch (you pay Setu).

**Note**: Production use requires KYC + Sahamati certification on Setu Bridge. For personal use, PDF upload is simpler and free.

## Job Tracker: configure your search

### 1. Upload your resume

Send a PDF named "resume" to the bot. Skills and target titles are extracted automatically.

### 2. Override in `.env` (optional)

```env
PROFILE_EXPERIENCE_YEARS=3  # Overrides resume's experience_years
PROFILE_SKILLS=python,go,aws  # Comma-separated (adds to resume skills)
PROFILE_LOCATIONS=Bangalore,Remote  # Preferred locations
PROFILE_MIN_SALARY=2500000  # Minimum annual salary in INR
```

### 3. Run a scan

```
/scan
```

Jobs are scored and ranked in the reply. Refine your profile and scan again.

### Scrapers

| Scraper | Key | Jobs per scan | Notes |
|---------|-----|---------------|-------|
| Greenhouse | None | ~15–30 | 36 company boards pre-configured |
| Ashby | None | ~5–8 | Open API, no key needed |
| LinkedIn | None | ~30 | India-filtered, works without auth |
| RemoteOK | None | ~20 | Remote-first, global |
| Adzuna | `ADZUNA_APP_ID` + `ADZUNA_API_KEY` | ~50+ | India jobs, free API key from developer.adzuna.com |

Enable/disable individual scrapers via `.env` (`GREENHOUSE_ENABLED=true` etc).

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From BotFather |
| `TELEGRAM_SECRET_TOKEN` | Yes | Random string for webhook security |
| `ALLOWED_TELEGRAM_USER_IDS` | Yes | Your Telegram user ID (comma-separated) |
| `DATABASE_URL` | Yes | Postgres connection string |
| `PUBLIC_BASE_URL` | Webhook | Public HTTPS URL (needed for Setu callbacks) |
| `GEMINI_API_KEY` | Yes | For AI spending chat (free tier: 20 req/day) |
| `SETU_CLIENT_ID` | Optional | Setu Bridge credentials |
| `SETU_CLIENT_SECRET` | Optional | Setu Bridge credentials |
| `SETU_PRODUCT_INSTANCE_ID` | Optional | Setu product ID |
| `JOB_SCAN_ENABLED` | No | Enable job tracker (default: true) |
| `COMPANY_MIN_EMPLOYEES` | No | Minimum company size (default: 500) |
| `PROFILE_EXPERIENCE_YEARS` | No | Overrides resume experience (default: resume value) |
| `PROFILE_SKILLS` | No | Extra skills beyond resume (comma-separated) |
| `PROFILE_TARGET_TITLES` | No | Override resume titles (comma-separated) |
| `PROFILE_LOCATIONS` | No | Preferred locations (comma-separated) |
| `PROFILE_MIN_SALARY` | No | Minimum annual salary in INR |
| `GREENHOUSE_ENABLED` | No | Enable Greenhouse scraper (default: true) |
| `ASHBY_ENABLED` | No | Enable Ashby scraper (default: true) |
| `LINKEDIN_ENABLED` | No | Enable LinkedIn scraper (default: true) |
| `REMOTEOK_ENABLED` | No | Enable RemoteOK scraper (default: true) |
| `ADZUNA_APP_ID` | No | Adzuna API app ID |
| `ADZUNA_API_KEY` | No | Adzuna API key |

Find your Telegram user ID: message [@userinfobot](https://t.me/userinfobot).

## Project structure

```
app/
├── main.py                  # FastAPI app + startup
├── config.py                # Pydantic settings
├── db/                      # SQLAlchemy models + session
│   ├── models.py            # User, Transaction, Consent, Job, ...
│   └── session.py           # Engine + SessionLocal
├── telegram/                # Bot client + handlers
│   ├── client.py            # Telegram API wrapper
│   ├── handler.py           # Message/document routing
│   └── security.py          # Access control
├── banking/                 # Setu AA integration
│   ├── setu_client.py       # Consent + data fetch API
│   ├── sync.py              # FIP mapping + ingestion
│   └── categorizer.py       # Rule-based spending categories
├── statements/              # PDF parsers
│   ├── pdf_parser.py        # Shared extract utilities
│   ├── credit_card.py       # Credit card statement parser
│   └── bank_statement.py    # Bank statement parser
├── chat/                    # Gemini AI agent
│   ├── agent.py             # Tool-calling loop with Gemini
│   └── tools.py             # Transaction query functions
├── jobs/                    # Job tracker module
│   ├── models.py            # Job, JobApplication, Company
│   ├── company_db.py        # 169 curated companies
│   ├── matcher.py           # Profile scoring + seniority filter
│   ├── scanner.py           # Scraper orchestrator
│   ├── telegram_commands.py # Bot command handlers
│   ├── router.py            # HTTP endpoints (/jobs/scan)
│   ├── config.py            # Job-specific settings
│   └── scrapers/
│       ├── greenhouse.py    # Greenhouse API
│       ├── ashby.py         # Ashby API (open)
│       ├── linkedin.py      # LinkedIn scraping
│       ├── remoteok.py      # RemoteOK API
│       └── adzuna.py        # Adzuna API (needs key)
├── routers/                 # FastAPI route modules
│   ├── telegram.py          # Telegram webhook endpoint
│   ├── setu.py              # Setu AA webhook
│   ├── health.py            # Health check
│   └── transactions.py      # Transaction API
└── scripts/
    └── run_polling.py       # Long-polling entry point
```

## Known limitations

- **Google Jobs scraper**: Blocked by Google (bot detection). Not included in active scrapers.
- **Lever scraper**: All 3 pre-configured boards (Shopify, Asana, Uber) return 404. Disabled by default.
- **Gemini free tier**: 20 requests/day. Upgrade at [ai.google.dev](https://ai.google.dev) for higher quotas.
- **Setu production**: Requires KYC + Sahamati certification. Sandbox works for testing; PDF upload is the practical path for personal use.
- **LinkedIn**: No API key needed but may rate-limit after frequent scans.

## License

Private / personal use.
