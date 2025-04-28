#!/usr/bin/env python3
import pyaudio
import numpy as np
import wave
import tempfile
import os
import time
from mlx_whisper.transcribe import transcribe
from deep_translator import GoogleTranslator

# Set up audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 4000  # Smaller chunks for more frequent updates
RECORD_SECONDS = 5

# MLX model path (optimized for Apple Silicon)
MODEL_PATH = "mlx-community/whisper-medium-mlx"

print("====== ENGLISH TO ITALIAN TRANSLATOR (MLX) ======")
print("Using MLX for optimal performance on Apple Silicon")
print("Speak in English, and see Italian translation below")
print("Press Ctrl+C to exit")
print("=================================================")

# Initialize translator
translator = GoogleTranslator(source='en', target='it')

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Start recording
stream = audio.open(format=FORMAT, channels=CHANNELS,
                rate=RATE, input=True,
                frames_per_buffer=CHUNK)

try:
    while True:
        # Record audio for a few seconds
        print("\nListening...")
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
        print("Transcribing...")
        result = transcribe(
            temp_filename,
            language="en",  # source language
            task="transcribe",  # transcribe task (not translate)
            path_or_hf_repo=MODEL_PATH
        )
        
        # Extract English transcription from segments
        english_text = ""
        for segment in result.get("segments", []):
            english_text += segment.get("text", "")
        
        # Step 2: Translate English text to Italian using deep-translator
        if english_text and english_text.strip() and len(english_text.strip()) > 1:
            print("English: " + english_text)
            print("Translating to Italian...")
            try:
                italian_text = translator.translate(english_text)
                if italian_text:
                    print("\n🇮🇹 " + italian_text)
                else:
                    print("Translation returned empty result")
            except Exception as e:
                print(f"Translation error: {e}")
                print("English text: " + english_text)
        else:
            if english_text.strip():
                print(f"Text too short to translate: '{english_text.strip()}'")
            else:
                print("No speech detected")
        
        # Clean up temporary file
        os.unlink(temp_filename)

except KeyboardInterrupt:
    print("\nStopping...")

# Clean up
stream.stop_stream()
stream.close()
audio.terminate()
print("Translation service stopped") 