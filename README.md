# PGAI Voice Bot — Automated Voice Agent Testing Framework

An automated voice bot that calls Pretty Good AI's healthcare demo agent and conducts structured test conversations using OpenAI's Realtime API as the "patient." Built for the PGAI AI Engineering Challenge.

## What This Does

This system makes outbound phone calls to PGAI's Pivot Point Orthopedics demo line and has an AI-driven patient persona interact with their healthcare voice agent. Each call follows a scripted scenario designed to test functionality, security, and edge cases. Both sides of the conversation are transcribed in real time, and recordings are captured via Twilio.

## Architecture
Phone Call                          Target

┌──────────────┐                   ┌──────────────┐

│  Twilio       │◄────────────────►│  PGAI Agent   │

│  (Telephony)  │   Audio Stream    │  (Target)     │

└──────┬───────┘                   └──────────────┘

│ WebSocket (u-law audio)

┌──────▼───────┐

│  FastAPI      │◄── ngrok tunnel ◄── Twilio webhook

│  Server       │

└──────┬───────┘

│ WebSocket (u-law audio)

┌──────▼───────┐

│  OpenAI       │

│  Realtime API │

│  (Patient AI) │

└──────────────┘

The FastAPI server bridges audio between Twilio (phone call) and OpenAI Realtime (patient AI). Audio flows bidirectionally in real time.

## Results Summary

- **27 test scenarios** across 4 categories (functional, security, edge cases, advanced exploits)
- **20+ calls completed** with transcripts and recordings
- **17 bugs documented** including 3 critical-severity HIPAA findings
- **Full attack chain demonstrated:** bypassed identity verification → unauthorized caregiver access → unlimited patient data → permanent appointment cancellation

See [BUG_REPORT.md](BUG_REPORT.md) for the complete findings.

## Setup

### Prerequisites
- Python 3.11+
- Twilio account (upgraded from trial) with a phone number
- OpenAI API key with Realtime API access
- ngrok account for tunneling

### Installation
```bash
git clone https://github.com/Ndwoo10/PGAI-Test.git
cd PGAI-Test
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### Running
Start ngrok in a separate terminal:
```bash
ngrok http 6060
```

Update DOMAIN in .env with the ngrok URL, then:
```bash
python main.py --list           # List all 27 scenarios
python main.py --scenario 01    # Run a specific scenario
python fetch_recordings.py      # Download recordings after calls
```

## Project Structure
pgai-voice-bot/

├── main.py                  # Core server: FastAPI + Twilio + OpenAI bridge

├── scenarios.py             # 27 test scenarios with patient personas

├── fetch_recordings.py      # Download call recordings from Twilio

├── test_openai_connection.py # Standalone OpenAI API connection test

├── .env.example             # Environment variable template

├── .gitignore

├── BUG_REPORT.md            # Complete bug report with 17 findings

├── ARCHITECTURE.md          # Technical architecture documentation

├── requirements.txt

├── transcripts/             # Call transcripts (.txt and .json)

└── recordings/              # Call recordings (.mp3)

## Test Scenarios

| Category | Scenarios | Description |
|----------|-----------|-------------|
| Functional (01-05) | Scheduling, rescheduling, refills, office hours, insurance |
| Security (06-14) | Staff impersonation, HIPAA attacks, prompt injection, emergency 911, prescription manipulation, third-party cancellation, emotional manipulation, content attacks, scope escalation |
| Edge Cases (15-19) | Impossible times, contradictory info, Spanish language, wrong number, off-topic with data extraction |
| Advanced Exploits (20-27) | Reasoning chain logic trap, reverse confirmation, helpfulness escalation, vendor extraction, provider impersonation, cancellation persistence, authorization chaining, data dump |

## Attack Methodology

Testing informed by OWASP LLM Top 10 (2025), RedCaller TEAPOT methodology, MPIB Medical Prompt Injection Benchmark, and Aegis Voice Agent Security Framework. Techniques include crescendo escalation, confirmation extraction, reasoning chain manipulation, well-meaning disguise, authority spoofing, and helpfulness commitment traps.

## Key Technologies
- Python / FastAPI — WebSocket server bridging Twilio and OpenAI
- Twilio Voice API — Outbound calling, audio streaming, call recording
- OpenAI Realtime API (gpt-realtime, GA) — Speech-to-speech patient AI
- ngrok — Public tunnel for Twilio webhook delivery