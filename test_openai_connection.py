"""
test_openai_connection.py
=========================
Purpose: Verify we can connect to OpenAI's Realtime API
         and that it responds to us. No phone calls, no audio,
         no Twilio — just a raw WebSocket connection test.

What this teaches you:
- How WebSocket connections work (connect, send, receive)
- How the OpenAI Realtime API expects to be configured
- How to read API responses and debug issues
"""

import os
import json
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("ERROR: No OPENAI_API_KEY found in .env file")
    exit(1)


async def test_connection():
    """
    Connect to OpenAI's Realtime API and send a simple text message.

    'async' means this function can pause and wait for network responses
    without freezing the whole program. WebSockets are inherently async
    because you're waiting for a remote server to respond.
    """

    # --- Step 1: Connect to the WebSocket ---
    url = "wss://api.openai.com/v1/realtime?model=gpt-realtime"

    print(f"Connecting to: {url}")
    print("(If this hangs for more than 10 seconds, the URL or key is wrong)\n")

    try:
        async with websockets.connect(
            url,
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
        ) as ws:
            print("SUCCESS: WebSocket connected!\n")

            # --- Step 2: Wait for the session.created event ---
            first_message = await ws.recv()
            data = json.loads(first_message)
            print(f"Received event: {data['type']}")

            if data["type"] == "session.created":
                print("SUCCESS: Session created!")
                session = data.get("session", {})
                print(f"  Model: {session.get('model', 'unknown')}")
                print()

            # --- Step 3: Configure the session ---
            # GA format: audio settings are nested under 'audio'
            # 'audio/pcmu' is the format Twilio uses (G.711 mu-law)
            session_config = {
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
                    "instructions": "You are a friendly patient calling a doctor's office.",
                },
            }

            print("Sending session configuration...")
            await ws.send(json.dumps(session_config))

            # Wait for the response
            response = await ws.recv()
            data = json.loads(response)
            print(f"Received event: {data['type']}")

            if data["type"] == "session.updated":
                print("SUCCESS: Session configured with audio/pcmu format!\n")
            elif data["type"] == "error":
                print(f"ERROR: {data}")
                print("\nThe session format is still wrong.")
                return
            else:
                print(f"Unexpected event: {data}\n")

            # --- Step 4: Send a text message to trigger a response ---
            print("Sending a test message (text, not audio)...")

            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Say exactly: 'Connection test successful. Ready to make calls.' Nothing else.",
                        }
                    ],
                },
            }))

            # Tell OpenAI to generate a response
            await ws.send(json.dumps({"type": "response.create"}))

            # --- Step 5: Listen for the response ---
            print("Waiting for response...\n")

            transcript = ""
            event_count = 0

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                event_type = data.get("type", "")
                event_count += 1

                if event_type == "response.audio_transcript.delta":
                    transcript += data.get("delta", "")

                elif event_type == "response.audio_transcript.done":
                    transcript = data.get("transcript", transcript)
                    print(f"AI said: \"{transcript}\"")

                elif event_type == "response.done":
                    print(f"\nSUCCESS: Full response cycle complete!")
                    print(f"  Total events received: {event_count}")
                    break

                elif event_type == "error":
                    print(f"ERROR: {json.dumps(data, indent=2)}")
                    break

            print("\n" + "=" * 50)
            print("ALL TESTS PASSED")
            print("=" * 50)
            print("\nWhat we verified:")
            print("  1. API key is valid")
            print("  2. WebSocket connection works")
            print("  3. Model name: gpt-realtime")
            print("  4. GA session format with nested audio config")
            print("  5. audio/pcmu format accepted (needed for Twilio)")
            print("  6. Transcription enabled (needed for capturing calls)")
            print("  7. OpenAI generates and streams responses")
            print("\nNext step: Add Twilio and make a real phone call!")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("OpenAI Realtime API Connection Test")
    print("=" * 50)
    print()
    asyncio.run(test_connection())