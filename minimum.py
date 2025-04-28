#!/usr/bin/env python3
import asyncio
import os
import json
import pyaudio
import tempfile
import wave
import logging
from aiohttp import web
from aiohttp_cors import setup as cors_setup, ResourceOptions, CorsViewMixin
from mlx_whisper.transcribe import transcribe
from deep_translator import GoogleTranslator

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PORT = 7878
MODEL_PATH = "mlx-community/whisper-medium-mlx"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 4000
RECORD_SECONDS = 3

translator = GoogleTranslator(source='en', target='it')
clients = set()

async def broadcast_message(message):
    if not clients:
        logger.debug("No clients connected to broadcast to")
        return
        
    logger.debug(f"Broadcasting to {len(clients)} clients")
    disconnected = set()
    
    for client in clients:
        try:
            data = f"data: {message}\n\n"
            await client.write(data.encode('utf-8'))
            await client.drain()
            logger.debug(f"Successfully sent message: {message}")
        except Exception as e:
            logger.error(f"Failed to send to client: {str(e)}")
            disconnected.add(client)
    
    clients.difference_update(disconnected)
    if disconnected:
        logger.debug(f"Removed {len(disconnected)} disconnected clients")

class SSEHandler(CorsViewMixin):
    async def get(self, request):
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
        logger.info(f"New client connected. Total clients: {len(clients)}")
        
        try:
            # Send initial connection confirmation
            await response.write(b'data: {"type":"connected"}\n\n')
            
            # Keep connection alive
            while True:
                await asyncio.sleep(1)
                if not response.prepared:
                    break
                
        except ConnectionResetError:
            logger.info("Client connection reset")
        except Exception as e:
            logger.error(f"Client connection error: {str(e)}")
        finally:
            if response in clients:
                clients.remove(response)
                logger.info(f"Client disconnected. Remaining clients: {len(clients)}")
        
        return response

async def process_audio():
    audio = pyaudio.PyAudio()
    try:
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        logger.info("Audio stream opened successfully")
    except Exception as e:
        logger.error(f"Audio error: {e}")
        return

    try:
        while True:
            try:
                # Record audio
                frames = []
                logger.debug("Recording audio chunk...")
                for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                logger.debug("Finished recording chunk")

                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_filename = temp_file.name
                    logger.debug(f"Saving to temp file: {temp_filename}")
                
                wf = wave.open(temp_filename, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()

                # Transcribe
                logger.debug("Transcribing audio...")
                result = transcribe(temp_filename, language="en", task="transcribe", path_or_hf_repo=MODEL_PATH)
                english_text = ''.join([seg.get("text", "") for seg in result.get("segments", [])])
                os.unlink(temp_filename)

                if english_text.strip():
                    logger.info(f"English text detected: {english_text}")
                    italian_text = translator.translate(english_text)
                    logger.info(f"Translated to Italian: {italian_text}")
                    
                    message = json.dumps({
                        "type": "translation",
                        "english": english_text.strip(),
                        "italian": italian_text.strip()
                    })
                    
                    # Ensure broadcast happens
                    try:
                        await broadcast_message(message)
                    except Exception as e:
                        logger.error(f"Failed to broadcast: {str(e)}")
                else:
                    logger.debug("No speech detected in audio chunk")

            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")
                await asyncio.sleep(1)
    finally:
        logger.info("Cleaning up audio resources")
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except:
            pass

async def run_server():
    app = web.Application()
    
    # Setup CORS
    cors = cors_setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_get('/translations', SSEHandler().get)
    app.router.add_static('/', '.')
    
    # Configure CORS for routes
    for route in list(app.router.routes()):
        cors.add(route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Server running at http://localhost:{PORT}")
    
    # Start audio processing in the background
    audio_task = asyncio.create_task(process_audio())
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        audio_task.cancel()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Exiting...")

