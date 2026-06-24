"""
main.py — PGAI Voice Bot Server v2
====================================
Usage:
    python main.py --list              Show all scenarios
    python main.py --scenario 01       Run scenario 01
    python main.py --scenario 08       Run scenario 08
"""

import os
import sys
import json
import base64
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
from dotenv import load_dotenv
import uvicorn
import re

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
PHONE_NUMBER_FROM = os.getenv("PHONE_NUMBER_FROM")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
raw_domain = os.getenv("DOMAIN", "")
DOMAIN = re.sub(r"(^\w+:|^)\/\/|\/+$", "", raw_domain)
PORT = int(os.getenv("PORT", 6060))
PGAI_TEST_NUMBER = "+18054398008"

SYSTEM_MESSAGE = ""
SCENARIO_ID = "01"
SCENARIO_NAME = ""
SCENARIO_CATEGORY = ""
CALL_SID = None
TRANSCRIPT = []
TURN_COUNTER = 0


def parse_args():
    """Parse command line arguments BEFORE doing anything else."""
    parser = argparse.ArgumentParser(description="PGAI Voice Bot")
    parser.add_argument("--scenario", help="Scenario ID (e.g., 01, 08, 15)")
    parser.add_argument("--list", action="store_true", help="List all scenarios")
    return parser.parse_args()


# Parse args FIRST — before any env validation or server setup
args = parse_args()

if args.list:
    from scenarios import list_scenarios
    list_scenarios()
    sys.exit(0)

if not args.scenario:
    print("\nUsage:")
    print("  python main.py --list              Show all scenarios")
    print("  python main.py --scenario 01       Run a scenario\n")
    sys.exit(0)

from scenarios import get_scenario

scenario = get_scenario(args.scenario)
if not scenario:
    print(f"\nERROR: Scenario '{args.scenario}' not found")
    from scenarios import list_scenarios
    list_scenarios()
    sys.exit(1)

SCENARIO_ID = args.scenario
SCENARIO_NAME = scenario["name"]
SCENARIO_CATEGORY = scenario.get("category", "unknown")

# Force English on all scenarios EXCEPT the Spanish test (17)
if SCENARIO_ID == "17":
    SYSTEM_MESSAGE = scenario["system_message"]
else:
    SYSTEM_MESSAGE = (
        "IMPORTANT: You MUST always respond in English regardless of what "
        "language you hear. Even if you hear Spanish or any other language, "
        "always reply in English.\n\n"
        + scenario["system_message"]
    )

# Now validate environment (only needed if we're making a call)
missing = []
for var_name, var_val in [
    ("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
    ("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
    ("PHONE_NUMBER_FROM", PHONE_NUMBER_FROM),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("DOMAIN", DOMAIN),
]:
    if not var_val:
        missing.append(var_name)

if missing:
    print(f"\nERROR: Missing environment variables: {', '.join(missing)}")
    print("Check your .env file.\n")
    sys.exit(1)

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
app = FastAPI()


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    global TRANSCRIPT, TURN_COUNTER

    print("\n--- Call connected! Audio streaming started ---\n")
    await websocket.accept()

    openai_url = "wss://api.openai.com/v1/realtime?model=gpt-realtime"

    async with websockets.connect(
        openai_url,
        additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
    ) as openai_ws:

        first_msg = await openai_ws.recv()
        print("OpenAI session created")

        await openai_ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        "turn_detection": {"type": "server_vad"},
                        "transcription": {"model": "whisper-1"},
                    },
                    "output": {
                        "format": {"type": "audio/pcmu"},
                        "voice": "ash",
                    },
                },
                "instructions": SYSTEM_MESSAGE,
            },
        }))

        update_msg = await openai_ws.recv()
        update_data = json.loads(update_msg)
        if update_data.get("type") == "session.updated":
            print("OpenAI session configured")
        else:
            print(f"Unexpected: {update_data}")

        stream_sid = None

        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data["event"] == "media":
                        try:
                            await openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": data["media"]["payload"],
                            }))
                        except Exception:
                            break
                    elif data["event"] == "start":
                        stream_sid = data["start"]["streamSid"]
                        print(f"Twilio stream started: {stream_sid}")
                    elif data["event"] == "stop":
                        print("Twilio stream stopped")
                        break
            except WebSocketDisconnect:
                print("Twilio disconnected")

        async def send_to_twilio():
            nonlocal stream_sid
            global TURN_COUNTER
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    event_type = response.get("type", "")

                    if event_type == "response.output_audio_transcript.done":
                        text = response.get("transcript", "")
                        if text.strip():
                            TURN_COUNTER += 1
                            TRANSCRIPT.append({
                                "turn": TURN_COUNTER,
                                "speaker": "Patient (Bot)",
                                "text": text.strip(),
                            })
                            print(f"  PATIENT: {text.strip()}")

                    if event_type == "conversation.item.input_audio_transcription.completed":
                        text = response.get("transcript", "")
                        if text.strip():
                            TURN_COUNTER += 1
                            TRANSCRIPT.append({
                                "turn": TURN_COUNTER,
                                "speaker": "PGAI Agent",
                                "text": text.strip(),
                            })
                            print(f"  AGENT:   {text.strip()}")

                    if event_type in ("response.audio.delta", "response.output_audio.delta"):
                        if response.get("delta") and stream_sid:
                            try:
                                audio = base64.b64encode(
                                    base64.b64decode(response["delta"])
                                ).decode("utf-8")
                                await websocket.send_json({
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": audio},
                                })
                            except Exception:
                                break

                    if event_type == "error":
                        error_info = response.get("error", {})
                        print(f"  [OpenAI Error] {error_info.get('message', response)}")

            except Exception as e:
                print(f"OpenAI connection ended: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

    save_transcript()
    print("\n--- Call complete! ---")
    print("Press Ctrl+C to stop the server, then run the next scenario.\n")


async def make_call():
    global CALL_SID
    twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response>"
        f'<Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect>'
        f"</Response>"
    )
    try:
        call = twilio_client.calls.create(
            from_=PHONE_NUMBER_FROM,
            to=PGAI_TEST_NUMBER,
            twiml=twiml,
            record=True,
            time_limit=180,
        )
        CALL_SID = call.sid
        print(f"Call initiated! SID: {CALL_SID}")
        print("Waiting for PGAI to answer...\n")
    except Exception as e:
        print(f"\nCALL FAILED: {e}")
        sys.exit(1)


def save_transcript():
    if not TRANSCRIPT:
        print("(No transcript captured)")
        return

    Path("transcripts").mkdir(exist_ok=True)

    # Clean scenario name for filename
    safe_name = SCENARIO_NAME.lower()
    for char in [":", "/", "—", "+", "'", '"']:
        safe_name = safe_name.replace(char, "")
    safe_name = safe_name.replace(" ", "-").replace("--", "-").strip("-")

    # Text file for human reading
    txt_file = f"transcripts/call-{SCENARIO_ID}-{safe_name}.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"PGAI Voice Bot — Call Transcript\n")
        f.write(f"Scenario {SCENARIO_ID}: {SCENARIO_NAME}\n")
        f.write(f"Category: {SCENARIO_CATEGORY}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Call SID: {CALL_SID}\n")
        f.write(f"{'=' * 50}\n\n")
        for turn in TRANSCRIPT:
            f.write(f"[{turn['speaker']}]\n{turn['text']}\n\n")
    print(f"Transcript saved to: {txt_file}")

    # JSON file for programmatic analysis
    json_file = f"transcripts/call-{SCENARIO_ID}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "scenario_id": SCENARIO_ID,
            "scenario_name": SCENARIO_NAME,
            "category": SCENARIO_CATEGORY,
            "call_sid": CALL_SID,
            "timestamp": datetime.now().isoformat(),
            "conversation": TRANSCRIPT,
        }, f, indent=2)


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print(f"  Scenario {SCENARIO_ID}: {SCENARIO_NAME}")
    print("=" * 50)
    print(f"  Target:  {PGAI_TEST_NUMBER}")
    print(f"  From:    {PHONE_NUMBER_FROM}")
    print(f"  Domain:  {DOMAIN}")
    print("=" * 50 + "\n")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_call())

    print("Starting server...\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")