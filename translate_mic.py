#!/usr/bin/env python3
import pyaudio
import numpy as np
import wave
import tempfile
import os
import time
from faster_whisper import WhisperModel

# Set up audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 4000  # Smaller chunks for more frequent updates
RECORD_SECONDS = 5

# Initialize Whisper model
print("Loading Whisper model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Model loaded!")

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Start recording
stream = audio.open(format=FORMAT, channels=CHANNELS,
                rate=RATE, input=True,
                frames_per_buffer=CHUNK)

print("====== ENGLISH TO ITALIAN TRANSLATOR ======")
print("Speak in English, and see Italian translation below")
print("Press Ctrl+C to exit")
print("==========================================")

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
        
        # Transcribe and translate with Whisper
        print("Translating...")
        segments, info = model.transcribe(temp_filename, task="translate")
        translation = " ".join([segment.text for segment in segments])
        
        # Display translation
        if translation.strip():
            print("\n🇮🇹 " + translation)
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