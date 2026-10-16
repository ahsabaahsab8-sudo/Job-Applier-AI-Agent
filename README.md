# 🤖 AI Job Hunter & Autonomous Application Agent 💼🚀

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Apify](https://img.shields.io/badge/Scraper-Apify%20Actor-green?logo=apify&logoColor=white)](https://apify.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20Notifications-2CA5E0?logo=telegram&logoColor=white)](https://telegram.org)
[![Gmail](https://img.shields.io/badge/Outreach-Gmail%20SMTP%20%2F%20OAuth-EA4335?logo=gmail&logoColor=white)](https://mail.google.com)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> ⚡ **An autonomous end-to-end recruitment agent that scrapes live job postings, scores fit against your resume with an LLM, identifies recruiter and HR emails with DNS validation, composes hyper-personalized cover letters, and dispatches tailored applications.**

---

## 🌟 Key Capabilities

* 🌐 **Multi-Board Aggregation**: Collects real-time job openings across LinkedIn, WeWorkRemotely, RemoteOK, and custom job boards via Apify.
* 🧠 **LLM Match Scoring & Semantic Filtering**: Compares candidate resume text with job requirements, scoring each opening from 0 to 100 with actionable rationales.
* 🔍 **Smart Recruiter Email Hunter**: Discovers hiring managers, talent acquisition specialists, and founders with DNS MX-record deliverability verification.
* ✍️ **Dynamic Pitch Customizer**: Writes context-aware, customized pitch emails tailored specifically to the company's tech stack and pain points.
* 📎 **Automated PDF Attachment Delivery**: Sends clean, professional emails with your resume PDF attached directly via Gmail SMTP or OAuth2.
* 📱 **Telegram Bot Controller**: Receive instant alerts on discovered jobs, approve applications with 1 click, inspect logs, or trigger ad-hoc runs remotely.
* 🛡️ **Built-in Safety & Dry Run**: `DRY_RUN=True` mode allows safe inspection of scored leads and generated email pitches without sending real emails.

---

## 🏗️ Architecture & Pipeline

```
┌─────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
│ Scraping Aggregator │ ───>  │  Resume Parser &     │ ───>  │ Recruiter Email &    │
│ (LinkedIn / Remote) │       │  LLM Relevance Score │       │ DNS MX Verification  │
└─────────────────────┘       └──────────────────────┘       └──────────┬───────────┘
                                                                        │
┌─────────────────────┐       ┌──────────────────────┐       ┌──────────▼───────────┐
│ Telegram Alert &    │ <───  │ Gmail SMTP Delivery  │ <───  │ Personalized Pitch   │
│ Application Log     │       │ + Resume PDF Attach  │       │ Generation (LLM)     │
└─────────────────────┘       └──────────────────────┘       └──────────────────────┘
```

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core orchestration, parsing, and pipeline |
| **Job Scraping** | Apify LinkedIn & Remote Actors | High-fidelity extraction of job descriptions |
| **AI / LLM Engine** | Kilo Code / OpenAI Compatible API | Resume evaluation, fit ranking, and pitch composition |
| **Email Verification** | `dnspython` & MX record lookup | Validates domain mail exchanger records before sending |
| **Mailer Engine** | Python `smtplib` / Google API Client | Automated outreach with PDF attachment support |
| **Scheduler** | `schedule` / Crontab / Systemd | Recurring autonomous runs |
| **Mobile Interface** | Python Telegram Bot | Alerts, approvals, and queue management |

---

## 🔑 Required Environment Variables (`.env`)

Configure `.env` using `.env.example`:

```bash
cp .env.example .env
```

| Variable | Required | Description |
| :--- | :---: | :--- |
| `APIFY_API_TOKEN` | **Yes** | Apify API token for running web scraping actors |
| `KILO_API_KEY` | **Yes** | LLM Gateway key for job scoring and pitch drafting |
| `KILO_BASE_URL` | No | Base endpoint (defaults to `https://api.kilo.ai/api/gateway/v1`) |
| `CANDIDATE_NAME` | **Yes** | Candidate's full name to sign outreach emails |
| `CANDIDATE_EMAIL` | **Yes** | Candidate's contact email address |
| `CANDIDATE_PORTFOLIO`| No | Portfolio or website URL |
| `CANDIDATE_GITHUB` | No | GitHub profile link |
| `RESUME_FILE` | **Yes** | Filename of your PDF resume (placed in root or codebase/) |
| `GMAIL_SENDER_EMAIL` | **Yes** | Your Google/Gmail address |
| `GMAIL_APP_PASSWORD` | **Yes** | 16-character Google App Password (not your main password) |
| `TARGET_ROLES` | **Yes** | Comma-separated target keywords (e.g. `Python, AI Engineer`) |
| `DAILY_JOB_LIMIT` | No | Max job applications sent per day (default: `50`) |
| `DRY_RUN` | **Yes** | Set `True` to preview without sending; `False` for production |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram Bot token for mobile updates |

---

## 🚀 Setup & Local Execution

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/ahsabaahsab8-sudo/Job-Applier-AI-Agent.git
cd Job-Applier-AI-Agent

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add Your Resume
Place your resume PDF in the repository root (e.g., `Resume.pdf`) and make sure `RESUME_FILE=Resume.pdf` in `.env`.

### 3. Dry-Run Test
```bash
# Run single test cycle in simulation mode
python agent.py --dry-run
```

### 4. Start Telegram Bot
```bash
python telegram_bot.py
```

---

## ☁️ Running 24/7 on a Linux VPS

### Option A: Systemd Background Service

```bash
sudo nano /etc/systemd/system/job-applier.service
```

Paste the following configuration:
```ini
[Unit]
Description=AI Job Applier Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Job-Applier-AI-Agent
EnvironmentFile=/opt/Job-Applier-AI-Agent/.env
ExecStart=/opt/Job-Applier-AI-Agent/venv/bin/python agent.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now job-applier
sudo systemctl status job-applier
```

---

## 📂 Project Organization

```
Job-Applier-AI-Agent/
├── .env.example          # Clean configuration blueprint
├── agent.py              # Main autonomous agent entrypoint
├── config.py             # Config validator & loader
├── email_finder.py       # Recruiter email discovery & DNS verification
├── mailer.py             # SMTP / Gmail email sender with attachments
├── pipeline.py           # Scrape -> Score -> Email pipeline flow
├── requirements.txt      # Python dependencies
├── resume_parser.py      # PDF text extractor and resume normalizer
├── scheduler.py          # Daily cron runner for scheduled applications
├── scorer.py             # LLM job-to-resume scoring engine
├── scraper.py            # Apify multi-source job board collector
├── storage.py            # Applied jobs database to prevent duplicate emails
├── telegram_bot.py       # Telegram notification and interactive control bot
└── test_gmail.py         # SMTP connectivity check script
```

---

## ⚠️ Responsible Automation Notice

* Always start with `DRY_RUN=True` to review email text and scoring quality before sending real emails.
* Comply with email provider rate limits to protect your domain reputation.
* Never spam recruiters; target only roles closely matching your genuine skills and experience.

---

## 📄 License

MIT License. Crafted with ❤️ for modern job seekers.
