# Architecture — PGAI Voice Bot

## System Overview

The PGAI Voice Bot is an automated testing framework that places outbound phone calls to a target voice AI agent and conducts adversarial conversations using OpenAI's Realtime API as the caller. The system captures both sides of the conversation as transcripts and audio recordings for analysis.

## Components

### 1. FastAPI Server (main.py)

The core of the system. Runs on port 6060 and serves a single WebSocket endpoint at `/media-stream`. When a call connects, it:

- Accepts the Twilio WebSocket connection carrying inbound audio (what the PGAI agent says)
- Opens a parallel WebSocket connection to OpenAI's Realtime API
- Pipes µ-law audio between the two connections bidirectionally
- Captures transcription events from OpenAI for both sides of the conversation
- Saves transcripts to disk as both human-readable .txt and machine-readable .json

### 2. Twilio Voice (telephony layer)

Handles the actual phone call. The server uses the Twilio REST API to initiate an outbound call to the PGAI test number (+1-805-439-8008). The call is configured with TwiML that tells Twilio to stream the call audio to our WebSocket endpoint via ngrok. Twilio also records the call server-side for later download.

### 3. OpenAI Realtime API (patient AI)

Acts as the "patient" on the phone call. Configured with a scenario-specific system prompt that defines the patient's name, DOB, phone number, and conversation goals. Uses the `gpt-realtime` model with server-side VAD (voice activity detection), Whisper transcription, and µ-law audio format matching Twilio's codec.

### 4. ngrok (tunnel)

Provides a public HTTPS/WSS URL that Twilio can reach. Required because the FastAPI server runs on localhost. Free tier provides a random subdomain that changes on restart.

### 5. Scenario Library (scenarios.py)

Contains 27 test scenarios organized into four categories. Each scenario defines a patient persona with specific identity details and conversational goals. The system message is injected into the OpenAI session at call start.

### 6. Recording Fetcher (fetch_recordings.py)

Downloads MP3 recordings from Twilio's API after calls complete. Matches recordings to scenarios using Call SID from the transcript JSON files.

## Audio Pipeline

```
PGAI Agent speaks
    → Twilio captures audio (µ-law 8kHz)
    → Twilio streams to FastAPI via WebSocket (base64-encoded)
    → FastAPI forwards to OpenAI Realtime API
    → OpenAI Whisper transcribes (input_audio_transcription.completed)
    → OpenAI generates spoken response (response.output_audio)
    → FastAPI forwards audio back to Twilio WebSocket
    → Twilio plays audio to PGAI Agent
    → PGAI Agent hears and responds
    → Cycle repeats
```

## Session Configuration (OpenAI Realtime API GA Format)

The OpenAI Realtime API GA release (2026) uses a different configuration format than the preview. Key differences discovered during development:

- Session requires `"type": "realtime"` field
- Audio config is nested under `audio.input` and `audio.output`
- Audio format uses `{"type": "audio/pcmu"}` not `"g711_ulaw"`
- Turn detection is nested under `audio.input.turn_detection`
- Transcript events use `response.output_audio_transcript.done` (not `response.audio_transcript.done`)

## Data Flow

```
Scenario selected (--scenario 01)
    → System message loaded from scenarios.py
    → English prefix added (except scenario 17)
    → Twilio REST API creates outbound call
    → Call connects, Twilio opens WebSocket
    → OpenAI session created and configured
    → Audio streams bidirectionally until call ends
    → Transcript saved to transcripts/call-{id}-{name}.txt
    → JSON saved to transcripts/call-{id}.json
    → Recording available via Twilio API (fetch_recordings.py)
```

## Key Technical Decisions

**Why OpenAI Realtime instead of STT→LLM→TTS pipeline?** Latency. The Realtime API handles speech-to-speech in a single model call, producing natural conversational timing. A traditional pipeline would add 2-4 seconds of latency per turn, making the conversation sound robotic.

**Why Twilio instead of direct SIP?** Twilio handles telephony complexity (call routing, codec negotiation, recording) and provides a clean WebSocket API for audio streaming. Direct SIP would require managing a PBX.

**Why µ-law audio?** Twilio's default codec for voice calls. Matching the codec avoids transcoding overhead and preserves audio quality.

**Why force English in the system prompt?** After running the Spanish test scenario (17), the OpenAI model began defaulting to Spanish on subsequent calls because it heard the PGAI agent's Spanish greeting. Adding "You MUST always respond in English" to the system prompt (except for the Spanish test) prevents this.
