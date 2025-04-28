#!/usr/bin/env python3
import pyaudio
import wave
import tempfile
import os
from mlx_whisper.transcribe import transcribe
from deep_translator import GoogleTranslator
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

# Audio settings
CHUNK = 4000
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 3

# Initialize translator
translator = GoogleTranslator(source='en', target='it')

def run_server():
    # Simple HTTP server
    server = HTTPServer(('localhost', 7878), SimpleHTTPRequestHandler)
    print("Server running at http://localhost:7878")
    print("Open http://localhost:7878/simple_ui.html in your browser")
    server.serve_forever()

def main():
    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                       rate=RATE, input=True,
                       frames_per_buffer=CHUNK)
    
    print("Listening... Speak in English")
    
    while True:
        try:
            # Record audio
            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                
            wf = wave.open(temp_filename, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            # Transcribe
            result = transcribe(temp_filename, language="en", task="transcribe")
            english_text = ''.join([seg.get("text", "") for seg in result.get("segments", [])])
            os.unlink(temp_filename)

            if english_text.strip():
                # Translate
                italian_text = translator.translate(english_text)
                print(f"English: {english_text}")
                print(f"Italian: {italian_text}")
                
                # Write to text file
                with open('translations.txt', 'w') as f:
                    f.write(f"{english_text.strip()}\n{italian_text.strip()}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user") 