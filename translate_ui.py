#!/usr/bin/env python3
import pyaudio
import numpy as np
import wave
import tempfile
import os
import time
import json
import asyncio
from mlx_whisper.transcribe import transcribe
from deep_translator import GoogleTranslator
from aiohttp import web
import webbrowser

# Set up audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 4000
RECORD_SECONDS = 3  # Shorter chunks for more responsive UI

# Use a single port for simplicity
PORT = 7878

# MLX model path (optimized for Apple Silicon)
MODEL_PATH = "mlx-community/whisper-medium-mlx"

# Initialize translator
translator = GoogleTranslator(source='en', target='it')

# Set for connected SSE clients
clients = set()

# Audio processing function with error handling
async def process_audio(app):
    audio = pyaudio.PyAudio()
    
    # Start recording
    try:
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        print("Please check your microphone settings and try again.")
        return
    
    print("====== ENGLISH TO ITALIAN TRANSLATOR (WEB UI) ======")
    print(f"Open http://localhost:{PORT} in your browser")
    print("Speak in English to see the Italian translation")
    print("Press Ctrl+C to exit")
    print("===================================================")
    
    try:
        while True:
            try:
                # Record audio for a few seconds
                frames = []
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                
                # Save to a temporary file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_filename = temp_file.name
                    
                wf = wave.open(temp_filename, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # Step 1: Transcribe English audio to English text
                result = transcribe(
                    temp_filename,
                    language="en",
                    task="transcribe",
                    path_or_hf_repo=MODEL_PATH
                )
                
                # Extract English transcription from segments
                english_text = ""
                for segment in result.get("segments", []):
                    english_text += segment.get("text", "")
                
                # Step 2: Translate English text to Italian using deep-translator
                if english_text and english_text.strip() and len(english_text.strip()) > 1:
                    english_text = english_text.strip()
                    print(f"English: {english_text}")
                    
                    try:
                        italian_text = translator.translate(english_text)
                        
                        if italian_text:
                            italian_text = italian_text.strip()
                            print(f"Italian: {italian_text}")
                            
                            # Send translation to UI via SSE
                            message = json.dumps({
                                "type": "translation",
                                "english": english_text,
                                "italian": italian_text
                            })
                            await broadcast_message(message)
                        else:
                            print("Translation returned empty result")
                    except Exception as e:
                        print(f"Translation error: {e}")
                else:
                    if english_text.strip():
                        print(f"Text too short to translate: '{english_text.strip()}'")
                
                # Clean up temporary file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                    
            except Exception as e:
                print(f"Error in audio processing: {e}")
                await asyncio.sleep(1)  # Sleep to avoid tight loop on errors
    
    except asyncio.CancelledError:
        print("\nStopping audio processing...")
    
    finally:
        # Clean up
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except:
            pass
        print("Translation service stopped")

# Function to broadcast messages to all clients
async def broadcast_message(message):
    if not clients:
        print("No clients connected to broadcast to")
        return
    
    print(f"Broadcasting to {len(clients)} clients: {message}")
    disconnected = set()
    
    for client in clients:
        try:
            # Format message as SSE data
            data = f"data: {message}\n\n"
            await client.write(data.encode('utf-8'))
            await client.drain()
            print("Successfully sent message")
        except Exception as e:
            print(f"Failed to send to client: {str(e)}")
            disconnected.add(client)
    
    clients.difference_update(disconnected)
    if disconnected:
        print(f"Removed {len(disconnected)} disconnected clients")

# SSE handler
async def sse_handler(request):
    response = web.StreamResponse(
        status=200,
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': '*',
        }
    )

    await response.prepare(request)
    clients.add(response)
    print(f"New client connected. Total clients: {len(clients)}")

    try:
        # Send initial connection confirmation
        await response.write(b'data: {"type":"connected"}\n\n')
        await response.drain()  # 🛠 ADD THIS LINE RIGHT HERE!!

        # Keep connection alive
        while True:
            await asyncio.sleep(1)
            if not response.prepared:
                break
    except ConnectionResetError:
        print("Client connection reset")
    except Exception as e:
        print(f"Client connection error: {str(e)}")
    finally:
        if response in clients:
            clients.remove(response)
            print(f"Client disconnected. Remaining clients: {len(clients)}")

    return response

# HTTP handler for serving the HTML
async def index_handler(request):
    return web.FileResponse('./translation_ui.html')

# Create and run the server
async def run_server():
    try:
        os.system(f"lsof -ti tcp:{PORT} | xargs kill -9")
        await asyncio.sleep(1)
    except:
        pass

    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/translations', sse_handler)
    app.router.add_static('/static/', './')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', PORT)

    # START SERVER FIRST
    await site.start()

    # THEN start audio recording
    audio_task = asyncio.create_task(process_audio(app))

    # Open browser
    webbrowser.open(f"http://localhost:{PORT}")

    print(f"✅ Server running at http://localhost:{PORT}")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        print("Server shutdown requested")
    finally:
        audio_task.cancel()
        await audio_task
        await runner.cleanup()
        print("Server stopped")
        
if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"Fatal error: {e}") 