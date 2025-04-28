#!/usr/bin/env python3
import pyaudio
import numpy as np
import wave
import tempfile
import os
import time
import threading
import json
import asyncio
from aiohttp import web
from mlx_whisper.transcribe import transcribe
from deep_translator import GoogleTranslator
import webbrowser
import socket

# Set up audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 4000
RECORD_SECONDS = 3  # Shorter chunks for more responsive UI

# Use a single port for both HTTP and WebSocket
PORT = 6872

# MLX model path (optimized for Apple Silicon)
MODEL_PATH = "mlx-community/whisper-medium-mlx"

# Initialize translator
translator = GoogleTranslator(source='en', target='it')

# Create HTML file with Apple Music-like lyrics UI
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Translation - Apple Music Style</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            margin: 0;
            padding: 0;
            background-color: #000;
            color: #fff;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            padding: 20px;
            text-align: center;
            background-color: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            z-index: 10;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .lyrics-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
            overflow: hidden;
            position: relative;
        }
        
        .background {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #1e3c72, #2a5298);
            filter: blur(50px);
            z-index: -1;
            opacity: 0.6;
            transition: background 2s ease;
        }
        
        .lyric-line {
            font-size: 32px;
            margin: 12px 0;
            text-align: center;
            opacity: 0.5;
            transform: scale(0.9);
            transition: all 0.5s ease;
            width: 100%;
            max-width: 800px;
            position: relative;
        }
        
        .lyric-line.active {
            opacity: 1;
            transform: scale(1);
            font-weight: 600;
        }
        
        .english {
            margin-bottom: 10px;
            color: #fff;
        }
        
        .italian {
            color: #A0E9FF;
            margin-bottom: 40px;
        }
        
        .status {
            position: fixed;
            bottom: 20px;
            left: 0;
            right: 0;
            text-align: center;
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
            padding: 10px;
        }
        
        .mic-icon {
            display: inline-block;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .mic-icon.listening {
            background-color: #4CAF50;
            animation: pulse 1.5s infinite;
        }
        
        .mic-icon.processing {
            background-color: #FFC107;
        }
        
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
            }
        }
        
        #lyrics-history {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            height: 100%;
            width: 100%;
            overflow-y: auto;
            padding-bottom: 100px;
            scroll-behavior: smooth;
        }
        
        .lyric-pair {
            margin-bottom: 40px;
            opacity: 0;
            transform: translateY(20px);
            animation: fadeIn 0.5s forwards;
        }
        
        @keyframes fadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @media (max-width: 768px) {
            .lyric-line {
                font-size: 24px;
            }
        }

        .connection-indicator {
            position: fixed;
            top: 10px;
            right: 10px;
            font-size: 12px;
            padding: 5px 10px;
            border-radius: 20px;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 100;
        }

        .connected {
            color: #4CAF50;
        }

        .disconnected {
            color: #F44336;
        }

        .connecting {
            color: #FFC107;
        }

        .retry-btn {
            display: inline-block;
            margin-left: 10px;
            padding: 3px 10px;
            background-color: #1e88e5;
            color: white;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="connection-indicator" id="connection">
        <span id="connection-status" class="connecting">Connecting...</span>
        <span class="retry-btn" id="retry-btn">Reconnect</span>
    </div>

    <div class="header">
        <h1>English to Italian Translator</h1>
        <p>Speak in English to see the Italian translation</p>
    </div>
    
    <div class="lyrics-container">
        <div class="background"></div>
        <div id="lyrics-history"></div>
    </div>
    
    <div class="status">
        <span class="mic-icon listening" id="status-icon"></span>
        <span id="status-text">Listening...</span>
    </div>

    <script>
        const lyricsHistory = document.getElementById('lyrics-history');
        const statusIcon = document.getElementById('status-icon');
        const statusText = document.getElementById('status-text');
        const background = document.querySelector('.background');
        const connectionStatus = document.getElementById('connection-status');
        const retryBtn = document.getElementById('retry-btn');
        
        // Function to generate a random gradient background
        function updateBackground() {
            const colors = [
                ['#1e3c72', '#2a5298'],
                ['#4B79A1', '#283E51'],
                ['#834d9b', '#d04ed6'],
                ['#0B486B', '#F56217'],
                ['#3A1C71', '#D76D77', '#FFAF7B'],
                ['#12c2e9', '#c471ed', '#f64f59'],
                ['#009688', '#26A69A']
            ];
            
            const randomColor = colors[Math.floor(Math.random() * colors.length)];
            const gradient = `linear-gradient(45deg, ${randomColor.join(', ')})`;
            background.style.background = gradient;
        }
        
        // Update background every 30 seconds
        updateBackground();
        setInterval(updateBackground, 30000);

        let ws;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        const reconnectDelay = 2000; // 2 seconds

        function connectWebSocket() {
            // Close existing connection if any
            if (ws) {
                ws.close();
            }

            connectionStatus.textContent = 'Connecting...';
            connectionStatus.className = 'connecting';
            
            // Get current host dynamically
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            
            // WebSocket connection - connect to /ws endpoint
            ws = new WebSocket(`${protocol}//${host}/ws`);
            
            ws.onopen = function() {
                console.log('Connected to translation server');
                connectionStatus.textContent = 'Connected';
                connectionStatus.className = 'connected';
                reconnectAttempts = 0;
                
                // Send a ping to ensure connection is working
                ws.send(JSON.stringify({type: 'ping'}));
            };
            
            ws.onmessage = function(event) {
                try {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'status') {
                        statusText.textContent = message.text;
                        statusIcon.className = 'mic-icon ' + message.status;
                    } 
                    else if (message.type === 'translation') {
                        // Create a new lyric pair container
                        const lyricPair = document.createElement('div');
                        lyricPair.className = 'lyric-pair';
                        
                        // Add English text
                        const englishLine = document.createElement('div');
                        englishLine.className = 'lyric-line english active';
                        englishLine.textContent = message.english;
                        lyricPair.appendChild(englishLine);
                        
                        // Add Italian translation
                        const italianLine = document.createElement('div');
                        italianLine.className = 'lyric-line italian active';
                        italianLine.textContent = message.italian;
                        lyricPair.appendChild(italianLine);
                        
                        // Add to history
                        lyricsHistory.appendChild(lyricPair);
                        
                        // Scroll to latest
                        lyricsHistory.scrollTop = lyricsHistory.scrollHeight;
                        
                        // Update background occasionally
                        if (Math.random() > 0.7) {
                            updateBackground();
                        }
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            ws.onclose = function(e) {
                console.log('WebSocket connection closed. Code:', e.code, 'Reason:', e.reason);
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.className = 'disconnected';
                
                // Try to reconnect automatically
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, reconnectDelay);
                    connectionStatus.textContent = `Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`;
                    connectionStatus.className = 'connecting';
                } else {
                    connectionStatus.textContent = 'Connection failed';
                    connectionStatus.className = 'disconnected';
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        // Manual reconnect button
        retryBtn.addEventListener('click', function() {
            reconnectAttempts = 0;
            connectWebSocket();
        });

        // Initial connection
        connectWebSocket();

        // Ping every 30 seconds to keep connection alive
        setInterval(function() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'ping'}));
            }
        }, 30000);
    </script>
</body>
</html>
"""

# Write HTML file
with open("translation_ui.html", "w") as f:
    f.write(HTML_CONTENT)

# Set for connected WebSocket clients
clients = set()

# Function to broadcast messages to all clients
async def broadcast_message(message):
    if not clients:
        return
    
    disconnected = set()
    for client in clients:
        try:
            await client.send_str(message)
        except Exception:
            disconnected.add(client)
    
    # Remove disconnected clients
    for client in disconnected:
        if client in clients:
            clients.remove(client)

# WebSocket handler
async def websocket_handler(request):
    # Prepare WebSocket response
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    print("Client connected to WebSocket")
    clients.add(ws)
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                # Handle ping messages to keep connection alive
                try:
                    data = json.loads(msg.data)
                    if data.get('type') == 'ping':
                        await ws.send_str(json.dumps({'type': 'pong'}))
                except json.JSONDecodeError:
                    pass
            elif msg.type == web.WSMsgType.ERROR:
                print(f"WebSocket connection closed with exception {ws.exception()}")
    finally:
        if ws in clients:
            clients.remove(ws)
        print("Client disconnected from WebSocket")
    
    return ws

# HTTP handler for serving the HTML
async def index_handler(request):
    return web.FileResponse('./translation_ui.html')

# Audio processing function
async def process_audio():
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
            # Update status to "listening"
            await broadcast_message(json.dumps({
                "type": "status",
                "status": "listening",
                "text": "Listening..."
            }))
            
            try:
                # Record audio for a few seconds
                frames = []
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                
                # Update status to "processing"
                await broadcast_message(json.dumps({
                    "type": "status",
                    "status": "processing",
                    "text": "Processing..."
                }))
                
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
                    print(f"English: {english_text}")
                    
                    try:
                        italian_text = translator.translate(english_text)
                        
                        if italian_text:
                            print(f"Italian: {italian_text}")
                            
                            # Send translation to UI
                            await broadcast_message(json.dumps({
                                "type": "translation",
                                "english": english_text,
                                "italian": italian_text
                            }))
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

# Main function to run the server
async def run_server():
    try:
        os.system(f"lsof -ti tcp:{PORT} | xargs kill -9 2>/dev/null || true")
        await asyncio.sleep(1)
    except:
        pass

    app = web.Application()
    app.router.add_get('/', index_handler)            # Serve HTML
    app.router.add_get('/ws', websocket_handler)       # WebSocket
    app.router.add_static('/static/', './')            # Optional: static assets (not needed unless you have JS/CSS)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

    print(f"Server running at http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")

    audio_task = asyncio.create_task(process_audio())

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