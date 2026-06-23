"""
fetch_recordings.py — Download call recordings from Twilio as mp3 files.
Run this after completing all test calls.

Usage:
    python fetch_recordings.py
"""

import os
import json
import requests
from pathlib import Path
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    print("ERROR: Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in .env")
    exit(1)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def fetch_all_recordings():
    Path("recordings").mkdir(exist_ok=True)
    print("\nFetching recordings from Twilio...\n")

    recordings = client.recordings.list()
    if not recordings:
        print("No recordings found.")
        return

    # Build a map of call SID -> scenario ID from transcript JSON files
    call_to_scenario = {}
    transcripts_dir = Path("transcripts")
    if transcripts_dir.exists():
        for json_file in transcripts_dir.glob("call-*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    if data.get("call_sid"):
                        call_to_scenario[data["call_sid"]] = {
                            "id": data.get("scenario_id", "unknown"),
                            "name": data.get("scenario_name", "unknown"),
                        }
            except (json.JSONDecodeError, KeyError):
                pass

    print(f"Found {len(recordings)} recording(s).\n")

    for i, recording in enumerate(recordings, 1):
        call_sid = recording.call_sid
        info = call_to_scenario.get(call_sid, {"id": f"unknown-{i:02d}", "name": "unknown"})
        scenario_id = info["id"]
        scenario_name = info["name"].lower().replace(" ", "-").replace(":", "").replace("/", "-")

        mp3_url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}"
            f"/Recordings/{recording.sid}.mp3"
        )

        filename = f"recordings/call-{scenario_id}-{scenario_name}.mp3"
        print(f"  Downloading: {filename}")
        print(f"    Duration: {recording.duration}s | Call SID: {call_sid}")

        response = requests.get(mp3_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))

        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"    Saved ({len(response.content) / 1024:.1f} KB)\n")
        else:
            print(f"    FAILED (HTTP {response.status_code})\n")

    print("Done! Check the recordings/ folder.\n")


if __name__ == "__main__":
    fetch_all_recordings()